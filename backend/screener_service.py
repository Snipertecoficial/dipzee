"""Market screener: runs the Opportunity Score across a TSX + US universe.

The universe is refreshed by the daily scheduler job and on demand. The query
endpoint reads from the assets collection and applies filters.

PROTOTYPE ONLY: data via yfinance. Replace with a licensed provider before charging.
"""
import logging
import time

from database import db
from asset_service import refresh_asset

logger = logging.getLogger(__name__)


class RefreshCooldownError(Exception):
    """Raised when a manual universe refresh is requested too soon after the last one."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"cooldown active, retry in {retry_after_seconds}s")


# A full pass fans out to hundreds of paid third-party market-data API calls
# (see UNIVERSE below), so on-demand refreshes (the customer "refresh" button
# on /screener and the admin panel's universe refresh) are throttled
# independently of the per-IP HTTP rate limiter — that limiter is keyed by
# caller, but the real constraint here is the SHARED provider quota, which
# any single low-tier subscriber could otherwise exhaust for every customer
# by hammering the button. The automated daily scheduler job is unaffected:
# it refreshes tickers directly (see scheduler.py) rather than through this
# function.
_REFRESH_COOLDOWN_SECONDS = 300
_last_manual_refresh = 0.0

# Curated universe of liquid TSX + US tickers spanning every major sector, so
# the screener has broad coverage instead of a handful of names. Refreshed
# once a day (see scheduler.daily_refresh_job) — a single ticker miss from the
# primary provider just falls through the resilient cascade to the next one
# (see providers.fetch_resilient), so this list can be large without risking
# an incomplete refresh.
UNIVERSE = [
    # US - Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "NVDA", "AVGO", "ORCL", "CRM", "ADBE",
    "CSCO", "INTC", "AMD", "QCOM", "TXN", "IBM", "INTU", "NOW", "AMAT", "MU",
    "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "PANW", "FTNT", "CRWD", "PYPL",
    "SHOP", "UBER", "ABNB", "PLTR", "SNOW", "DDOG", "NET", "ZS", "ROKU",
    "COIN", "SPOT", "SQ",
    # US - Communication Services
    "T", "VZ", "TMUS", "CMCSA", "NFLX", "DIS", "CHTR", "EA", "TTWO", "WBD",
    # US - Financial Services
    "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "BLK", "AXP", "USB", "PNC",
    "TFC", "COF", "SPGI", "MCO", "ICE", "CME", "V", "MA", "BK", "MET", "PRU",
    "AIG", "TRV", "ALL", "PGR",
    # US - Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "CVS", "CI", "ELV", "HUM", "MDT", "ISRG", "SYK", "BSX",
    "ZTS", "REGN", "VRTX", "BIIB",
    # US - Consumer Cyclical
    "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "MAR",
    "GM", "F", "TGT", "ROST", "YUM", "CMG", "ORLY", "AZO",
    # US - Consumer Defensive
    "WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "MDLZ", "CL", "KMB", "GIS",
    "KHC", "STZ", "SYY", "ADM", "KR",
    # US - Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB",
    "KMI", "HES", "DVN",
    # US - Industrials
    "BA", "HON", "UPS", "RTX", "CAT", "DE", "LMT", "GE", "MMM", "UNP", "NSC",
    "CSX", "ETN", "EMR", "ITW", "PH", "GD", "NOC", "WM", "FDX",
    # US - Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC", "PEG", "ES",
    # US - Real Estate
    "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "DLR", "AVB",
    # US - Materials
    "LIN", "SHW", "APD", "ECL", "NEM", "FCX", "NUE", "DOW", "DD", "PPG",
    # TSX
    "ENB.TO", "T.TO", "BCE.TO", "RY.TO", "TD.TO", "BNS.TO", "CM.TO", "BMO.TO",
    "FTS.TO", "CNR.TO", "SU.TO", "MFC.TO", "CP.TO", "TRP.TO", "CNQ.TO",
    "IMO.TO", "POW.TO", "SLF.TO", "GWO.TO", "WCN.TO", "ATD.TO", "L.TO",
    "QSR.TO", "NA.TO", "MRU.TO", "TRI.TO", "BAM.TO", "MG.TO", "WN.TO",
]


async def refresh_universe(limit: int | None = None) -> int:
    """Refresh universe tickers into the assets collection. Returns count refreshed."""
    global _last_manual_refresh
    now = time.time()
    elapsed = now - _last_manual_refresh
    if elapsed < _REFRESH_COOLDOWN_SECONDS:
        raise RefreshCooldownError(int(_REFRESH_COOLDOWN_SECONDS - elapsed))
    _last_manual_refresh = now

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
