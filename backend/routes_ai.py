"""AI Virtual Analyst (LLM) — gated to Pro + Investor.

Generates an educational, structured interpretation of an asset by feeding the
Dipzee opportunity score + market data into an LLM (Anthropic Claude or Google
Gemini, selected via ``AI_PROVIDER`` — see ``ai_providers.py``). Responses are
localized (pt/en/es/fr) and cached per ``ticker+locale`` in Mongo for 12h to
control cost and latency.
"""
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ai_providers import AIProviderError, get_ai_provider
from asset_service import refresh_asset
from database import db
from providers import get_company_news
from security import require_feature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

CACHE_TTL_HOURS = 12
_LANG_NAMES = {"pt": "Portuguese (Brazil)", "en": "English", "es": "Spanish", "fr": "French"}
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# The 12h cache makes normal usage free after the first request per
# ticker+locale, but `?refresh=1` deliberately bypasses it and pays for a
# real LLM call — with no per-user cap, a script could hammer that param and
# run up real API cost (paid LLM tokens, not just our own compute) well
# beyond what a single subscription is worth. Throttle forced refreshes
# per-user, independent of the general per-IP rate limiter.
_FORCED_REFRESH_COOLDOWN_SECONDS = 120
_last_forced_refresh: dict = {}  # user_id -> monotonic timestamp


def _num(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def _build_context(asset: dict) -> dict:
    price = asset.get("price")
    target = asset.get("target_mean")
    upside = None
    if price and target:
        try:
            upside = round((float(target) - float(price)) / float(price) * 100, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            upside = None
    sub = asset.get("sub_scores") or {}
    return {
        "ticker": asset.get("ticker"),
        "name": asset.get("name"),
        "exchange": asset.get("exchange"),
        "sector": asset.get("sector"),
        "currency": asset.get("currency"),
        "price": _num(price),
        "change_pct": _num(asset.get("change_pct")),
        "low_52w": _num(asset.get("low_52w")),
        "high_52w": _num(asset.get("high_52w")),
        "target_mean": _num(target),
        "upside_pct": upside,
        "dividend_yield": _num(asset.get("dividend_yield")),
        "opportunity_score": asset.get("score"),
        "classification": asset.get("classification"),
        "sub_scores": {
            "buy_zone": _num(sub.get("buy")),
            "upside": _num(sub.get("upside")),
            "income": _num(sub.get("income")),
        },
    }


def _headlines(ticker: str, limit: int = 5):
    try:
        news = get_company_news(ticker, days=7, limit=limit) or []
        return [n.get("headline") for n in news if n.get("headline")][:limit]
    except Exception:  # noqa: BLE001
        return []


def _clean_json(text: str) -> dict:
    """Best-effort parse of a JSON object from an LLM completion."""
    if not text:
        raise ValueError("empty completion")
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _as_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:6]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


async def _generate(context: dict, headlines: list, locale: str) -> dict:
    try:
        provider = await get_ai_provider()
    except AIProviderError as e:
        logger.error("[ai analyst] provider not configured: %s", e)
        raise HTTPException(status_code=503, detail="AI analyst not configured")

    lang = _LANG_NAMES.get(locale, "English")
    system = (
        "You are Dipzee's Virtual Analyst, a concise buy-side equity analyst. "
        "You receive structured market data and an internal 'opportunity score' (0-100, higher = more attractive entry). "
        "Produce an EDUCATIONAL interpretation — never financial advice. "
        f"Respond ONLY with a valid minified JSON object, and write every human-readable string in {lang}. "
        "Schema: {"
        "\"summary\": string (2-3 sentences), "
        "\"stance\": one of [\"accumulate\",\"hold\",\"watch\",\"avoid\"], "
        "\"stance_label\": short localized label for the stance, "
        "\"thesis\": string[] (2-4 bullet points, the bull case), "
        "\"risks\": string[] (2-4 bullet points), "
        "\"catalysts\": string[] (1-3 bullet points), "
        "\"horizon\": short localized string (e.g. 'medium term'), "
        "\"confidence\": integer 0-100"
        "}. Do not include markdown, comments, or any text outside the JSON."
    )
    payload = {"asset": context, "recent_headlines": headlines}
    user_text = (
        "Analyze this asset and return the JSON described in the system prompt.\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        completion = await provider.generate(system, user_text)
    except Exception as e:  # noqa: BLE001
        logger.warning("[ai analyst] %s completion failed: %s", provider.name, e)
        raise HTTPException(status_code=502, detail="AI analyst failed to generate")

    parsed = _clean_json(completion)

    conf = parsed.get("confidence")
    try:
        conf = max(0, min(100, int(conf)))
    except (TypeError, ValueError):
        conf = None

    return {
        "summary": str(parsed.get("summary", "")).strip(),
        "stance": str(parsed.get("stance", "watch")).strip().lower(),
        "stance_label": str(parsed.get("stance_label", "")).strip(),
        "thesis": _as_list(parsed.get("thesis")),
        "risks": _as_list(parsed.get("risks")),
        "catalysts": _as_list(parsed.get("catalysts")),
        "horizon": str(parsed.get("horizon", "")).strip(),
        "confidence": conf,
    }


@router.get("/analyst/{ticker}")
async def ai_analyst(
    ticker: str,
    refresh: int = Query(0),
    user: dict = Depends(require_feature("ai_analyst")),
):
    ticker = ticker.strip().upper()
    locale = user.get("locale") or "en"
    if locale not in _LANG_NAMES:
        locale = "en"

    cache_key = {"ticker": ticker, "locale": locale}
    now = datetime.now(timezone.utc)

    if not refresh:
        cached = await db.ai_analyses.find_one(cache_key, {"_id": 0})
        if cached:
            try:
                fetched = datetime.fromisoformat(cached["generated_at"])
                if fetched.tzinfo is None:
                    fetched = fetched.replace(tzinfo=timezone.utc)
                if now - fetched < timedelta(hours=CACHE_TTL_HOURS):
                    cached["cached"] = True
                    return cached
            except Exception:  # noqa: BLE001
                pass
    else:
        last = _last_forced_refresh.get(user["id"], 0.0)
        elapsed = time.monotonic() - last
        if elapsed < _FORCED_REFRESH_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail={"message": f"Please wait {int(_FORCED_REFRESH_COOLDOWN_SECONDS - elapsed)}s before forcing another AI refresh."},
            )
        _last_forced_refresh[user["id"]] = time.monotonic()

    asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

    context = _build_context(asset)
    headlines = _headlines(ticker)

    try:
        analysis = await _generate(context, headlines, locale)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("[ai analyst] generation failed for %s: %s", ticker, e)
        raise HTTPException(status_code=502, detail="AI analyst failed to generate")

    doc = {
        "ticker": ticker,
        "locale": locale,
        "name": asset.get("name"),
        "opportunity_score": asset.get("score"),
        "classification": asset.get("classification"),
        **analysis,
        "generated_at": now.isoformat(),
        "cached": False,
    }
    await db.ai_analyses.update_one(cache_key, {"$set": doc}, upsert=True)
    doc.pop("_id", None)
    return doc
