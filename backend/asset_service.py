"""Asset refresh service: fetch via provider, compute score, upsert in Mongo."""
import logging
from datetime import datetime, timezone
from typing import Optional

from database import db
from providers import get_provider
from scoring import compute_opportunity_score, SETTINGS

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def refresh_asset(ticker: str) -> Optional[dict]:
    """Fetch fresh data for a ticker, compute the score and upsert the asset doc.

    Returns the stored asset dict, or None if the provider has no data and we
    have nothing cached.
    """
    ticker = ticker.strip().upper()
    provider = get_provider()
    existing = await db.assets.find_one({"ticker": ticker}, {"_id": 0})

    data = provider.fetch(ticker)
    if not data:
        logger.warning("No provider data for %s; returning cached doc if any", ticker)
        return existing

    score_res = compute_opportunity_score(
        data.get("price"), data.get("low_52w"), data.get("high_52w"),
        data.get("target_mean"), data.get("dividend_yield"), SETTINGS,
    )

    doc = {
        "ticker": ticker,
        "exchange": data.get("exchange"),
        "name": data.get("name"),
        "currency": data.get("currency"),
        "price": data.get("price"),
        "low_52w": data.get("low_52w"),
        "high_52w": data.get("high_52w"),
        "target_mean": data.get("target_mean"),
        "dividend_yield": data.get("dividend_yield"),
        "sector": data.get("sector"),
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
    return stored
