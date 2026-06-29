"""Market-data service behind a swappable DataProvider interface.

PROTOTYPE ONLY: The first implementation uses the free `yfinance` library which
scrapes Yahoo Finance. This is fine for prototyping/validation but it is NOT
licensed for commercial redistribution and data can be delayed/rate-limited.
BEFORE CHARGING CUSTOMERS this MUST be replaced by a licensed provider such as
Financial Modeling Prep (FMP) or Finnhub. The DataProvider abstraction below is
designed so the source can be swapped without touching the rest of the app.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_dividend_yield(info: dict) -> float:
    """Normalize dividendYield to a DECIMAL fraction (e.g. 0.0098 = 0.98%).

    yfinance versions are inconsistent: some return 0.0098, some 0.98 (percent).
    Strategy: cross-check against dividendRate/price (true decimal) when available
    and pick the closest candidate; otherwise fall back to a safe heuristic.
    """
    dy = info.get("dividendYield")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")

    implied = None
    if rate and price and price > 0:
        implied = rate / price

    if dy is None:
        return implied if implied is not None else 0.0

    try:
        dy = float(dy)
    except (TypeError, ValueError):
        return implied if implied is not None else 0.0

    candidate_decimal = dy
    candidate_pct = dy / 100.0

    if implied is not None and implied > 0:
        if abs(candidate_decimal - implied) <= abs(candidate_pct - implied):
            return candidate_decimal
        return candidate_pct

    # No ground truth: a real yield > 1.0 (=100%) is impossible -> it's a percent.
    if dy > 1.0:
        return candidate_pct
    return candidate_decimal


def _derive_exchange(symbol: str, info: dict) -> str:
    exch = info.get("fullExchangeName") or info.get("exchange")
    if exch:
        return str(exch)
    if symbol.upper().endswith(".TO"):
        return "TSX"
    if symbol.upper().endswith(".V"):
        return "TSXV"
    return "NASDAQ/NYSE"


class DataProvider(ABC):
    """Contract every market-data source must satisfy."""

    name: str = "base"

    @abstractmethod
    def fetch(self, symbol: str) -> Optional[dict]:
        """Return a normalized dict for one ticker or None when unavailable."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> list:
        """Return a list of {ticker, name, exchange} candidates."""
        raise NotImplementedError


class YFinanceProvider(DataProvider):
    name = "yfinance"

    def fetch(self, symbol: str) -> Optional[dict]:
        import yfinance as yf

        symbol = symbol.strip().upper()
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
        except Exception as e:  # noqa: BLE001 - never crash the API on provider errors
            logger.warning("yfinance fetch failed for %s: %s", symbol, e)
            return None

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        low = info.get("fiftyTwoWeekLow")
        high = info.get("fiftyTwoWeekHigh")
        if price is None and low is None and high is None:
            # Yahoo returned an empty payload (bad ticker / rate limited)
            return None

        return {
            "ticker": symbol,
            "exchange": _derive_exchange(symbol, info),
            "name": info.get("longName") or info.get("shortName") or symbol,
            "currency": info.get("currency") or "USD",
            "price": price,
            "low_52w": low,
            "high_52w": high,
            "target_mean": info.get("targetMeanPrice"),
            "dividend_yield": normalize_dividend_yield(info),
            "sector": info.get("sector"),
        }

    def search(self, query: str) -> list:
        import yfinance as yf

        query = query.strip()
        results = []
        try:
            s = yf.Search(query, max_results=8)
            for q in (s.quotes or []):
                sym = q.get("symbol")
                if not sym:
                    continue
                results.append({
                    "ticker": sym,
                    "name": q.get("longname") or q.get("shortname") or sym,
                    "exchange": q.get("exchange") or "",
                })
        except Exception as e:  # noqa: BLE001
            logger.warning("yfinance search failed for %s: %s", query, e)

        if not results and query:
            # Fall back to treating the query itself as a ticker symbol
            results.append({"ticker": query.upper(), "name": query.upper(), "exchange": ""})
        return results


# Singleton accessor so the source can be swapped in one place later.
_provider: Optional[DataProvider] = None


def get_provider() -> DataProvider:
    global _provider
    if _provider is None:
        _provider = YFinanceProvider()
    return _provider
