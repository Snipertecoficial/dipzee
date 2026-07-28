"""Intelligence surface (L3): explainable, gated, rate-limited insight endpoints.

Composes the deterministic substrate (knowledge graph + enriched market events +
optional LSE data) into localized briefs via the intelligence agents. Every
endpoint requires auth + a plan feature; the LLM-composed ones are cached per
key for 6h and throttle forced refreshes per user (LLM cost control), mirroring
routes_ai. No raw LSE redistribution — output is Dipzee-derived analysis.
"""
import logging
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from database import db
from security import require_feature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/intel", tags=["intelligence"])

CACHE_TTL_HOURS = 6
_FORCED_REFRESH_COOLDOWN_SECONDS = 120
_last_forced_refresh: dict = {}   # (user_id, kind) -> monotonic ts
_VALID_LOCALES = {"en", "pt", "es", "fr"}


def _locale(user: dict) -> str:
    loc = user.get("locale") or "en"
    return loc if loc in _VALID_LOCALES else "en"


def _fresh(doc: dict) -> bool:
    try:
        gen = datetime.fromisoformat(doc["generated_at"])
        if gen.tzinfo is None:
            gen = gen.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - gen < timedelta(hours=CACHE_TTL_HOURS)
    except Exception:  # noqa: BLE001
        return False


def _check_cooldown(user_id: str, kind: str):
    last = _last_forced_refresh.get((user_id, kind), 0.0)
    elapsed = time.monotonic() - last
    if elapsed < _FORCED_REFRESH_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail={
            "message": f"Please wait {int(_FORCED_REFRESH_COOLDOWN_SECONDS - elapsed)}s before forcing another refresh."})
    _last_forced_refresh[(user_id, kind)] = time.monotonic()


@router.get("/asset/{ticker}")
async def asset_intel(ticker: str, refresh: int = Query(0),
                      user: dict = Depends(require_feature("news_correlation"))):
    """Composed, explainable insight for one asset (score + news + optional options)."""
    from intelligence.agents import build_asset_context, explain_asset

    ticker = ticker.strip().upper()
    locale = _locale(user)
    key = {"ticker": ticker, "locale": locale}

    if not refresh:
        cached = await db.intel_insights.find_one(key, {"_id": 0})
        if cached and _fresh(cached):
            cached["cached"] = True
            return cached
    else:
        _check_cooldown(user["id"], "asset")

    context = await build_asset_context(db, ticker)
    if not context.get("name") and context.get("event_count", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    try:
        insight = await explain_asset(context, locale)
    except RuntimeError as e:
        logger.error("[intel] AI not configured: %s", e)
        raise HTTPException(status_code=503, detail="Intelligence not configured")
    except Exception as e:  # noqa: BLE001
        logger.warning("[intel] asset insight failed for %s: %s", ticker, e)
        raise HTTPException(status_code=502, detail="Intelligence failed to generate")

    doc = {**key, "name": context.get("name"), "sector": context.get("sector"),
           "opportunity_score": context.get("opportunity_score"),
           **insight, "generated_at": datetime.now(timezone.utc).isoformat(), "cached": False}
    await db.intel_insights.update_one(key, {"$set": doc}, upsert=True)
    doc.pop("_id", None)
    return doc


@router.get("/events/{ticker}")
async def asset_events(ticker: str, user: dict = Depends(require_feature("news_correlation"))):
    """Recent enriched market events affecting an asset (deterministic, no LLM)."""
    from event_service import recent_events
    from intelligence.agents import net_impact_from_events
    ticker = ticker.strip().upper()
    events = await recent_events(db, symbol=ticker, limit=20)
    impact = net_impact_from_events(events, ticker)
    return {"ticker": ticker, "net_impact": impact["net_impact"],
            "event_count": impact["event_count"], "events": events}


@router.get("/macro")
async def macro_intel(refresh: int = Query(0), user: dict = Depends(require_feature("macro_context"))):
    """Localized macro brief from recent macro/commodity events (cached 6h, shared)."""
    from intelligence.agents import macro_snapshot, explain_macro
    locale = _locale(user)
    key = {"id": "macro", "locale": locale}

    if not refresh:
        cached = await db.intel_macro.find_one(key, {"_id": 0})
        if cached and _fresh(cached):
            cached["cached"] = True
            return cached
    else:
        _check_cooldown(user["id"], "macro")

    snapshot = await macro_snapshot(db)
    try:
        brief = await explain_macro(snapshot, locale)
    except RuntimeError as e:
        logger.error("[intel] AI not configured: %s", e)
        raise HTTPException(status_code=503, detail="Intelligence not configured")
    except Exception as e:  # noqa: BLE001
        logger.warning("[intel] macro brief failed: %s", e)
        raise HTTPException(status_code=502, detail="Intelligence failed to generate")

    doc = {**key, **brief, "factors": snapshot.get("factors"),
           "generated_at": datetime.now(timezone.utc).isoformat(), "cached": False}
    await db.intel_macro.update_one(key, {"$set": doc}, upsert=True)
    doc.pop("_id", None)
    return doc


@router.get("/options/{ticker}")
async def options_intel(ticker: str, user: dict = Depends(require_feature("options_flow"))):
    """Deterministic LSE options-flow summary for an asset (no LLM)."""
    from intelligence.agents import summarize_options_flow
    ticker = ticker.strip().upper()
    return {"ticker": ticker, "options": await summarize_options_flow(ticker)}
