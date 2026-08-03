"""Asset refresh service: fetch via provider, compute score, upsert in Mongo."""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from database import db
from providers import fetch_resilient, get_yf_target, fmp_target
from scoring import compute_opportunity_score, SETTINGS

logger = logging.getLogger(__name__)

# Real ticker symbols are short and only ever use this charset (letters,
# digits, a dot for share classes like BRK.B, a hyphen for feeds that use
# BRK-B instead). This is the single chokepoint almost every ticker-shaped
# input passes through before reaching provider URL-building code, so
# rejecting anything outside this shape here also protects providers.py's
# f-string-interpolated request URLs from query/path injection.
_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")
_SENSITIVE_QUERY_KEYS = {"apikey", "api_key", "key", "token", "access_token"}


def normalize_ticker(ticker: str) -> str:
    value = (ticker or "").strip().upper()
    if not _TICKER_RE.fullmatch(value):
        raise ValueError("Invalid ticker")
    return value


def sanitize_external_url(url: Optional[str]) -> Optional[str]:
    """Remove credentials accidentally embedded in provider-owned URLs."""
    if not url:
        return None
    try:
        parts = urlsplit(str(url))
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k.lower() not in _SENSITIVE_QUERY_KEYS]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    except Exception:
        return None


def sanitize_asset_for_client(asset: Optional[dict]) -> Optional[dict]:
    if not asset:
        return asset
    clean = dict(asset)
    clean.pop("_id", None)
    clean["logo"] = sanitize_external_url(clean.get("logo"))
    return clean


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def refresh_asset(ticker: str, force_target: bool = False) -> Optional[dict]:
    """Fetch fresh data for a ticker, compute the score and upsert the asset doc.

    Real-time price/52w/dividend/sector come from the primary provider (Finnhub).
    The analyst target is premium on Finnhub, so it is supplied by yfinance and
    cached on the asset: reused on fast/real-time refreshes, re-fetched when
    missing or when force_target=True (daily job).

    Returns the stored asset dict, or None if there is no data at all.
    """
    try:
        ticker = normalize_ticker(ticker)
    except ValueError:
        logger.warning("refresh_asset: rejected malformed ticker %r", ticker)
        return None
    existing = await db.assets.find_one({"ticker": ticker}, {"_id": 0})

    # Resilient cascade: try each source until one returns usable data. Offloaded
    # to a worker thread — these are blocking HTTP calls (requests/yfinance) and
    # running them inline would stall the whole event loop (all other requests)
    # for the duration of every refresh, including the daily/manual bulk ones.
    data = await asyncio.to_thread(fetch_resilient, ticker)
    if not data:
        logger.warning("No provider data for %s; returning cached doc if any", ticker)
        return existing

    # Analyst target feeds the Opportunity Score's upside sub-score. Prefer the
    # licensed FMP consensus; keep the cached value when present (unless the
    # daily job forces a refresh); yfinance is the last-resort fallback.
    target = data.get("target_mean")
    if target is None:
        if existing and existing.get("target_mean") and not force_target:
            target = existing.get("target_mean")
        else:
            target = await asyncio.to_thread(fmp_target, ticker)
            if target is None:
                target = await asyncio.to_thread(get_yf_target, ticker)

    score_res = compute_opportunity_score(
        data.get("price"), data.get("low_52w"), data.get("high_52w"),
        target, data.get("dividend_yield"), SETTINGS,
    )

    doc = {
        "ticker": ticker,
        "exchange": data.get("exchange"),
        "name": data.get("name"),
        "currency": data.get("currency"),
        "price": data.get("price"),
        "low_52w": data.get("low_52w"),
        "high_52w": data.get("high_52w"),
        "target_mean": target,
        "dividend_yield": data.get("dividend_yield"),
        "sector": data.get("sector"),
        "change_pct": data.get("change_pct"),
        "prev_close": data.get("prev_close"),
        "logo": sanitize_external_url(data.get("logo")),
        "source": data.get("source"),
        "updated_at": _now_iso(),
    }

    # Keep previous values so the alert engine can edge-trigger on changes.
    if existing:
        doc["prev_price"] = existing.get("price")
        doc["prev_dividend_yield"] = existing.get("dividend_yield")
        doc["prev_score"] = existing.get("score")
        doc["prev_flags"] = existing.get("flags")

    if score_res:
        doc["score"] = score_res["score"]
        doc["sub_scores"] = score_res["sub_scores"]
        doc["classification"] = score_res["classification"]
        doc["flags"] = score_res["flags"]
        doc["range_position"] = score_res["R"]
    else:
        doc["score"] = None
        doc["sub_scores"] = None
        doc["classification"] = None
        doc["flags"] = {"buy_zone": False, "sell_zone": False, "income": False}
        doc["range_position"] = None

    await db.assets.update_one({"ticker": ticker}, {"$set": doc}, upsert=True)
    stored = await db.assets.find_one({"ticker": ticker}, {"_id": 0})
    return sanitize_asset_for_client(stored)
