"""Market screener: runs the Opportunity Score across a TSX + US universe.

The universe is refreshed by the daily scheduler job and on demand. The query
endpoint reads from the assets collection and applies filters.

PROTOTYPE ONLY: data via yfinance. Replace with a licensed provider before charging.
"""
import logging

from database import db
from asset_service import refresh_asset

logger = logging.getLogger(__name__)

# Curated universe of liquid TSX + US tickers (dividend / value oriented).
UNIVERSE = [
    # US
    "AAPL", "MSFT", "KO", "JNJ", "PG", "VZ", "T", "XOM", "CVX", "PFE",
    "INTC", "CSCO", "IBM", "MMM", "JPM", "BAC", "WMT", "HD", "MCD", "PEP",
    # TSX
    "ENB.TO", "T.TO", "BCE.TO", "RY.TO", "TD.TO", "BNS.TO", "CM.TO", "BMO.TO",
    "FTS.TO", "CNR.TO", "SU.TO", "MFC.TO",
]


async def refresh_universe(limit: int | None = None) -> int:
    """Refresh universe tickers into the assets collection. Returns count refreshed."""
    tickers = UNIVERSE[:limit] if limit else UNIVERSE
    count = 0
    for tk in tickers:
        try:
            asset = await refresh_asset(tk)
            if asset and asset.get("score") is not None:
                count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("[screener] refresh failed for %s: %s", tk, e)
    logger.info("[screener] universe refreshed: %d/%d", count, len(tickers))
    return count


async def query_screener(filters: dict) -> list:
    query = {"score": {"$ne": None}}
    if filters.get("sector"):
        query["sector"] = filters["sector"]
    if filters.get("classification"):
        query["classification"] = filters["classification"]
    if filters.get("min_dividend") is not None:
        query["dividend_yield"] = {"$gte": float(filters["min_dividend"])}
    if filters.get("max_range_position") is not None:
        query["range_position"] = {"$lte": float(filters["max_range_position"])}

    assets = await db.assets.find(query, {"_id": 0}).to_list(500)

    # min_upside (to analyst target) computed in Python
    min_upside = filters.get("min_upside")
    out = []
    for a in assets:
        price = a.get("price")
        target = a.get("target_mean")
        upside = ((target - price) / price) if (target and price and price > 0) else None
        a["upside_target"] = round(upside, 4) if upside is not None else None
        if min_upside is not None:
            if upside is None or upside < float(min_upside):
                continue
        out.append(a)

    out.sort(key=lambda x: (x.get("score") if x.get("score") is not None else -1), reverse=True)
    return out


async def list_sectors() -> list:
    sectors = await db.assets.distinct("sector", {"sector": {"$ne": None}})
    return sorted([s for s in sectors if s])
