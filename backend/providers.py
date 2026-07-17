"""Market-data service behind a swappable DataProvider interface.

PROTOTYPE ONLY: The first implementation uses the free `yfinance` library which
scrapes Yahoo Finance. This is fine for prototyping/validation but it is NOT
licensed for commercial redistribution and data can be delayed/rate-limited.
BEFORE CHARGING CUSTOMERS this MUST be replaced by a licensed provider such as
Financial Modeling Prep (FMP) or Finnhub. The DataProvider abstraction below is
designed so the source can be swapped without touching the rest of the app.
"""
import logging
import os
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

import requests

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

        return results


# Singleton accessor so the source can be swapped in one place later.
_provider: Optional[DataProvider] = None


FINNHUB_BASE = "https://finnhub.io/api/v1"


class FinnhubProvider(DataProvider):
    """Primary provider: real-time quote + 52w range + dividend + sector + news.

    Analyst price target is a premium Finnhub endpoint, so the target is filled
    by yfinance (see get_yf_target) inside the asset service when missing.
    """

    name = "finnhub"

    def _key(self):
        return os.environ.get("FINNHUB_API_KEY")

    def _get(self, path: str, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["token"] = key
        try:
            r = requests.get(f"{FINNHUB_BASE}{path}", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:  # noqa: BLE001
            logger.warning("finnhub %s failed: %s", path, e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        quote = self._get("/quote", {"symbol": symbol})
        if not quote or not quote.get("c"):
            return None
        price = quote.get("c")
        profile = self._get("/stock/profile2", {"symbol": symbol}) or {}
        metric = (self._get("/stock/metric", {"symbol": symbol, "metric": "all"}) or {}).get("metric", {}) or {}

        low = metric.get("52WeekLow")
        high = metric.get("52WeekHigh")
        dy_raw = metric.get("dividendYieldIndicatedAnnual")
        if dy_raw is None:
            dy_raw = metric.get("currentDividendYieldTTM")
        # Finnhub returns dividend yield in PERCENT units (e.g. 0.38 = 0.38%).
        div = (float(dy_raw) / 100.0) if dy_raw is not None else 0.0

        return {
            "ticker": symbol,
            "exchange": profile.get("exchange") or _derive_exchange(symbol, {}),
            "name": profile.get("name") or symbol,
            "currency": profile.get("currency") or "USD",
            "price": price,
            "low_52w": low,
            "high_52w": high,
            "target_mean": None,  # premium on Finnhub -> filled by yfinance
            "dividend_yield": div,
            "sector": profile.get("finnhubIndustry"),
            "change_pct": quote.get("dp"),
            "prev_close": quote.get("pc"),
            "logo": profile.get("logo"),
            "source": "finnhub",
        }

    def search(self, query: str) -> list:
        d = self._get("/search", {"q": query}) or {}
        results = []
        for r in (d.get("result", []) or [])[:10]:
            sym = r.get("symbol")
            if not sym:
                continue
            results.append({"ticker": sym, "name": r.get("description") or sym, "exchange": r.get("type") or ""})
        return results


# --------------------------------------------------------------------------- #
# FMP Provider
# --------------------------------------------------------------------------- #
class FMPProvider(DataProvider):
    """Financial Modeling Prep, on their current `/stable` API.

    FMP retired the whole `/api/v3` family (legacy, cut off 2025-08-31) in
    favor of `/stable`, which also changed how symbols are passed (query
    param instead of URL path) and moved dividend yield from
    key-metrics-ttm to ratios-ttm. Endpoints not covered by the caller's plan
    (e.g. non-US quotes, screener, batch quotes on lower tiers) respond
    ``402 Payment Required``, which `_get` already treats as "no data" so the
    resilient cascade in this module just falls through to the next provider.
    """

    name = "fmp"
    FMP_BASE = "https://financialmodelingprep.com/stable"

    def _key(self):
        return os.environ.get("FMP_API_KEY")

    def _get(self, path: str, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["apikey"] = key
        try:
            r = requests.get(f"{self.FMP_BASE}{path}", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            logger.warning("FMP %s failed: %s", path, e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        # 1. Quote (price, 52w range, change, exchange, name)
        quote_list = self._get("/quote", {"symbol": symbol})
        if not quote_list or not isinstance(quote_list, list):
            return None
        q = quote_list[0]
        price = q.get("price")
        if price is None:
            return None

        # 2. Profile (currency, sector, logo, full company name)
        profile_list = self._get("/profile", {"symbol": symbol})
        p = profile_list[0] if profile_list and isinstance(profile_list, list) else {}

        # 3. TTM ratios (dividend yield, already a decimal fraction e.g. 0.032 = 3.2%)
        ratios_list = self._get("/ratios-ttm", {"symbol": symbol})
        r = ratios_list[0] if ratios_list and isinstance(ratios_list, list) else {}
        dy_raw = r.get("dividendYieldTTM")
        div = float(dy_raw) if dy_raw is not None else 0.0

        return {
            "ticker": symbol,
            "exchange": q.get("exchange") or p.get("exchange") or _derive_exchange(symbol, {}),
            "name": q.get("name") or p.get("companyName") or symbol,
            "currency": p.get("currency") or "USD",
            "price": price,
            "low_52w": q.get("yearLow"),
            "high_52w": q.get("yearHigh"),
            "target_mean": None,
            "dividend_yield": div,
            "sector": p.get("sector"),
            "change_pct": q.get("changePercentage"),
            "prev_close": q.get("previousClose"),
            "logo": p.get("image"),
            "source": "fmp",
        }

    def search(self, query: str) -> list:
        d = self._get("/search-name", {"query": query, "limit": 10}) or []
        results = []
        if isinstance(d, list):
            for r in d:
                sym = r.get("symbol")
                if not sym:
                    continue
                results.append({
                    "ticker": sym,
                    "name": r.get("name") or sym,
                    "exchange": r.get("exchangeFullName") or r.get("exchange") or "",
                })
        return results


# --------------------------------------------------------------------------- #
# Polygon Provider
# --------------------------------------------------------------------------- #
class PolygonProvider(DataProvider):
    name = "polygon"

    def _key(self):
        return os.environ.get("POLYGON_API_KEY")

    def _get(self, path: str, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["apiKey"] = key
        try:
            r = requests.get(f"https://api.polygon.io{path}", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            logger.warning("Polygon %s failed: %s", path, e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        snap = self._get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}", {})
        if not snap or snap.get("status") != "OK" or "ticker" not in snap:
            return None
        t_data = snap["ticker"]
        
        details = self._get(f"/v3/reference/tickers/{symbol}", {}) or {}
        results = details.get("results", {}) or {}

        price = t_data.get("lastTrade", {}).get("p") or t_data.get("min", {}).get("c")
        if price is None:
            return None

        logo = results.get("branding", {}).get("logo_url")
        if logo and "apiKey=" not in logo:
            logo = f"{logo}?apiKey={self._key()}"

        return {
            "ticker": symbol,
            "exchange": results.get("primary_exchange") or _derive_exchange(symbol, {}),
            "name": results.get("name") or symbol,
            "currency": results.get("currency_name") or "USD",
            "price": price,
            "low_52w": None,
            "high_52w": None,
            "target_mean": None,
            "dividend_yield": 0.0,
            "sector": results.get("sic_description"),
            "change_pct": t_data.get("todaysChangePerc"),
            "prev_close": t_data.get("prevDay", {}).get("c"),
            "logo": logo,
            "source": "polygon",
        }

    def search(self, query: str) -> list:
        d = self._get("/v3/reference/tickers", {"search": query, "limit": 10}) or {}
        results = []
        for r in (d.get("results", []) or []):
            sym = r.get("ticker")
            if not sym:
                continue
            results.append({
                "ticker": sym,
                "name": r.get("name") or sym,
                "exchange": r.get("primary_exchange") or ""
            })
        return results


# --------------------------------------------------------------------------- #
# Alpha Vantage Provider
# --------------------------------------------------------------------------- #
class AlphaVantageProvider(DataProvider):
    name = "alphavantage"

    def _key(self):
        return os.environ.get("ALPHAVANTAGE_API_KEY")

    def _get(self, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["apikey"] = key
        try:
            r = requests.get("https://www.alphavantage.co/query", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            logger.warning("AlphaVantage query failed: %s", e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        q_data = self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        if not q_data or "Global Quote" not in q_data:
            return None
        q = q_data["Global Quote"]
        
        price_str = q.get("05. price")
        if not price_str:
            return None
        price = float(price_str)

        ov = self._get({"function": "OVERVIEW", "symbol": symbol}) or {}

        low_str = ov.get("52WeekLow")
        high_str = ov.get("52WeekHigh")
        dy_str = ov.get("DividendYield")
        pct_str = str(q.get("10. change percent", "")).replace("%", "")

        try:
            low = float(low_str) if low_str else None
            high = float(high_str) if high_str else None
            div = float(dy_str) if dy_str else 0.0
            change_pct = float(pct_str) if pct_str else None
            prev = float(q.get("08. previous close")) if q.get("08. previous close") else None
            target = float(ov.get("AnalystTargetPrice")) if ov.get("AnalystTargetPrice") else None
        except Exception:
            low, high, div, change_pct, prev, target = None, None, 0.0, None, None, None

        return {
            "ticker": symbol,
            "exchange": ov.get("Exchange") or _derive_exchange(symbol, {}),
            "name": ov.get("Name") or symbol,
            "currency": ov.get("Currency") or "USD",
            "price": price,
            "low_52w": low,
            "high_52w": high,
            "target_mean": target,
            "dividend_yield": div,
            "sector": ov.get("Sector"),
            "change_pct": change_pct,
            "prev_close": prev,
            "logo": None,
            "source": "alphavantage",
        }

    def search(self, query: str) -> list:
        d = self._get({"function": "SYMBOL_SEARCH", "keywords": query}) or {}
        results = []
        for r in (d.get("bestMatches", []) or []):
            sym = r.get("1. symbol")
            if not sym:
                continue
            results.append({
                "ticker": sym,
                "name": r.get("2. name") or sym,
                "exchange": r.get("4. region") or ""
            })
        return results


# --------------------------------------------------------------------------- #
# Twelve Data Provider
# --------------------------------------------------------------------------- #
class TwelveDataProvider(DataProvider):
    name = "twelvedata"

    def _key(self):
        return os.environ.get("TWELVEDATA_API_KEY")

    def _get(self, path: str, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["apikey"] = key
        try:
            r = requests.get(f"https://api.twelvedata.com{path}", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            logger.warning("TwelveData %s failed: %s", path, e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        q = self._get("/quote", {"symbol": symbol})
        if not q or "price" not in q or q.get("code") == 400:
            return None
        
        p = self._get("/profile", {"symbol": symbol}) or {}

        try:
            price = float(q.get("close") or q.get("price"))
            low = float(q.get("fifty_two_week", {}).get("low")) if q.get("fifty_two_week", {}).get("low") else None
            high = float(q.get("fifty_two_week", {}).get("high")) if q.get("fifty_two_week", {}).get("high") else None
            change_pct = float(q.get("percent_change")) if q.get("percent_change") else None
            prev = float(q.get("previous_close")) if q.get("previous_close") else None
        except Exception:
            return None

        return {
            "ticker": symbol,
            "exchange": q.get("exchange") or _derive_exchange(symbol, {}),
            "name": q.get("name") or symbol,
            "currency": q.get("currency") or "USD",
            "price": price,
            "low_52w": low,
            "high_52w": high,
            "target_mean": None,
            "dividend_yield": 0.0,
            "sector": p.get("sector"),
            "change_pct": change_pct,
            "prev_close": prev,
            "logo": p.get("logo"),
            "source": "twelvedata",
        }

    def search(self, query: str) -> list:
        d = self._get("/symbol_search", {"symbol": query}) or {}
        results = []
        for r in (d.get("data", []) or [])[:10]:
            sym = r.get("symbol")
            if not sym:
                continue
            results.append({
                "ticker": sym,
                "name": r.get("instrument_name") or sym,
                "exchange": r.get("exchange") or ""
            })
        return results


# --------------------------------------------------------------------------- #
# Marketstack Provider
# --------------------------------------------------------------------------- #
class MarketstackProvider(DataProvider):
    name = "marketstack"

    def _key(self):
        return os.environ.get("MARKETSTACK_API_KEY")

    def _get(self, path: str, params: dict):
        key = self._key()
        if not key:
            return None
        params = dict(params)
        params["access_key"] = key
        try:
            r = requests.get(f"https://api.marketstack.com/v1{path}", params=params, timeout=12)
            if r.status_code >= 400:
                return None
            return r.json()
        except Exception as e:
            logger.warning("Marketstack %s failed: %s", path, e)
            return None

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        t_details = self._get(f"/tickers/{symbol}", {})
        if not t_details or "symbol" not in t_details:
            return None
        
        eod = self._get(f"/tickers/{symbol}/eod/latest", {}) or {}
        price = eod.get("close")
        if price is None:
            return None

        exch = t_details.get("stock_exchange", {}) or {}

        return {
            "ticker": symbol,
            "exchange": exch.get("acronym") or exch.get("name") or _derive_exchange(symbol, {}),
            "name": t_details.get("name") or symbol,
            "currency": "USD",
            "price": price,
            "low_52w": None,
            "high_52w": None,
            "target_mean": None,
            "dividend_yield": 0.0,
            "sector": None,
            "change_pct": None,
            "prev_close": eod.get("open"),
            "logo": None,
            "source": "marketstack",
        }

    def search(self, query: str) -> list:
        d = self._get("/tickers", {"search": query}) or {}
        results = []
        for r in (d.get("data", []) or [])[:10]:
            sym = r.get("symbol")
            if not sym:
                continue
            exch = r.get("stock_exchange", {}) or {}
            results.append({
                "ticker": sym,
                "name": r.get("name") or sym,
                "exchange": exch.get("acronym") or exch.get("name") or ""
            })
        return results


# --------------------------------------------------------------------------- #
# Investing.com Provider
# --------------------------------------------------------------------------- #
class InvestingProvider(DataProvider):
    name = "investing"

    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.investing.com/",
            "domain-id": "1"
        }

    def fetch(self, symbol: str) -> Optional[dict]:
        symbol = symbol.strip().upper()
        search_url = f"https://api.investing.com/api/search/v2/search?q={symbol}"
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=12)
            if r.status_code >= 400:
                return None
            search_res = r.json() or {}
        except Exception as e:
            logger.warning("Investing search failed for fetch %s: %s", symbol, e)
            return None

        quotes = search_res.get("quotes", []) or []
        pair_id = None
        name = symbol
        exch = "US"
        
        for q in quotes:
            if q.get("symbol", "").upper() == symbol:
                pair_id = q.get("pairId")
                name = q.get("name") or symbol
                exch = q.get("exchange") or "US"
                break
        
        if not pair_id and quotes:
            pair_id = quotes[0].get("pairId")
            name = quotes[0].get("name") or symbol
            exch = quotes[0].get("exchange") or "US"
            
        if not pair_id:
            return None

        inst_url = f"https://endpoints.investing.com/pd-instruments/v1/instruments?instrument_ids={pair_id}&domain_id=1"
        try:
            r = requests.get(inst_url, headers=self._headers(), timeout=12)
            if r.status_code >= 400:
                return None
            data = r.json() or {}
        except Exception as e:
            logger.warning("Investing instrument fetch failed for pair %s: %s", pair_id, e)
            return None

        inst_list = data.get("data", []) or []
        if not inst_list:
            if isinstance(data, list):
                inst_list = data
            elif "instruments" in data:
                inst_list = data["instruments"]

        if not inst_list:
            return None

        inst = inst_list[0]
        price = inst.get("last") or inst.get("price")
        if price is None:
            return None

        try:
            price = float(price)
            low = float(inst.get("52_week_low") or inst.get("low")) if (inst.get("52_week_low") or inst.get("low")) else None
            high = float(inst.get("52_week_high") or inst.get("high")) if (inst.get("52_week_high") or inst.get("high")) else None
            change_pct = float(inst.get("change_percent")) if inst.get("change_percent") else None
            prev = float(inst.get("prev_close") or inst.get("close")) if (inst.get("prev_close") or inst.get("close")) else None
        except Exception:
            return None

        return {
            "ticker": symbol,
            "exchange": exch or _derive_exchange(symbol, {}),
            "name": name,
            "currency": inst.get("currency") or "USD",
            "price": price,
            "low_52w": low,
            "high_52w": high,
            "target_mean": None,
            "dividend_yield": 0.0,
            "sector": inst.get("sector"),
            "change_pct": change_pct,
            "prev_close": prev,
            "logo": None,
            "source": "investing",
        }

    def search(self, query: str) -> list:
        search_url = f"https://api.investing.com/api/search/v2/search?q={query}"
        results = []
        try:
            r = requests.get(search_url, headers=self._headers(), timeout=12)
            if r.status_code >= 400:
                return []
            data = r.json() or {}
            for q in (data.get("quotes", []) or []):
                sym = q.get("symbol")
                if not sym:
                    continue
                results.append({
                    "ticker": sym,
                    "name": q.get("name") or sym,
                    "exchange": q.get("exchange") or ""
                })
        except Exception as e:
            logger.warning("Investing search failed: %s", e)
        return results


def get_company_news(symbol: str, days: int = 7, limit: int = 15) -> list:
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        return []
    symbol = symbol.strip().upper()
    to = date.today()
    frm = to - timedelta(days=days)
    try:
        r = requests.get(
            f"{FINNHUB_BASE}/company-news",
            params={"symbol": symbol, "from": frm.isoformat(), "to": to.isoformat(), "token": key},
            timeout=12,
        )
        if r.status_code >= 400:
            return []
        data = r.json() or []
    except Exception as e:  # noqa: BLE001
        logger.warning("finnhub company-news failed for %s: %s", symbol, e)
        return []
    out = []
    for a in data[:limit]:
        out.append({
            "id": a.get("id"),
            "headline": a.get("headline"),
            "summary": a.get("summary"),
            "url": a.get("url"),
            "source": a.get("source"),
            "image": a.get("image"),
            "datetime": a.get("datetime"),
        })
    return out


def get_market_news(limit: int = 20) -> list:
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        return []
    try:
        r = requests.get(f"{FINNHUB_BASE}/news", params={"category": "general", "token": key}, timeout=12)
        if r.status_code >= 400:
            return []
        data = r.json() or []
    except Exception:  # noqa: BLE001
        return []
    return [{
        "id": a.get("id"), "headline": a.get("headline"), "summary": a.get("summary"),
        "url": a.get("url"), "source": a.get("source"), "image": a.get("image"), "datetime": a.get("datetime"),
    } for a in data[:limit]]


def get_fmp_news(limit: int = 20) -> list:
    """Optional secondary news source: Financial Modeling Prep (needs FMP_API_KEY)."""
    key = os.environ.get("FMP_API_KEY")
    if not key:
        return []
    try:
        r = requests.get(
            "https://financialmodelingprep.com/api/v3/stock_news",
            params={"limit": limit, "apikey": key}, timeout=12,
        )
        if r.status_code >= 400:
            return []
        data = r.json() or []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for a in data[:limit]:
        out.append({
            "id": a.get("url"), "headline": a.get("title"), "summary": a.get("text"),
            "url": a.get("url"), "source": a.get("site"), "image": a.get("image"),
            "datetime": a.get("publishedDate"),
        })
    return out


_MARKET_NEWS_TICKERS = [
    "SPY", "QQQ", "DIA", "IWM",  # broad market
    "XLF", "XLK", "XLE", "XLV",  # financials / tech / energy / healthcare
]


def get_yf_news(symbol: Optional[str] = None, limit: int = 20) -> list:
    """News via yfinance's Ticker.news — needs no API key, so it's the fallback
    when Finnhub/FMP news are unavailable (missing key or plan-restricted).

    With a symbol: news for that ticker. Without: aggregates across a handful
    of broad-market index ETFs as a stand-in for a general market-news feed
    (yfinance has no dedicated "front page" news endpoint).
    """
    import yfinance as yf

    tickers = [symbol.strip().upper()] if symbol else _MARKET_NEWS_TICKERS
    seen = set()
    out = []
    for tk in tickers:
        try:
            items = yf.Ticker(tk).news or []
        except Exception as e:  # noqa: BLE001
            logger.warning("yfinance news failed for %s: %s", tk, e)
            continue
        for item in items:
            c = item.get("content") or {}
            nid = item.get("id") or c.get("id")
            if not nid or nid in seen:
                continue
            seen.add(nid)
            url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
            thumb = (c.get("thumbnail") or {}).get("originalUrl")
            out.append({
                "id": nid,
                "headline": c.get("title"),
                "summary": c.get("summary"),
                "url": url,
                "source": (c.get("provider") or {}).get("displayName") or "Yahoo Finance",
                "image": thumb,
                "datetime": c.get("pubDate"),
            })
    out.sort(key=lambda x: x.get("datetime") or "", reverse=True)
    return out[:limit]


def get_yf_target(symbol: str):
    """Best-effort analyst mean target via yfinance (Finnhub target is premium)."""
    try:
        import yfinance as yf
        info = yf.Ticker(symbol.strip().upper()).info or {}
        t = info.get("targetMeanPrice")
        return float(t) if t else None
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# Resilient multi-source cascade (works without paid API keys)
# --------------------------------------------------------------------------- #
# Circuit breaker for fragile scraping sources (e.g. Investing.com internal
# endpoints): after repeated failures we stop hitting them for a cooldown so a
# flaky/blocked source never slows down or crashes the whole request path.
_FRAGILE_SOURCES = {"investing"}
_BREAKER: dict = {}
_BREAKER_THRESHOLD = 3
_BREAKER_COOLDOWN = 600  # seconds


def _breaker_open(name: str) -> bool:
    import time
    b = _BREAKER.get(name)
    return bool(b and b.get("until", 0) > time.time())


def _breaker_record(name: str, ok: bool) -> None:
    import time
    if ok:
        _BREAKER.pop(name, None)
        return
    b = _BREAKER.setdefault(name, {"fails": 0, "until": 0.0})
    b["fails"] += 1
    if b["fails"] >= _BREAKER_THRESHOLD:
        b["until"] = time.time() + _BREAKER_COOLDOWN
        b["fails"] = 0


def _quote_chain() -> list:
    """Ordered list of providers to try for a single quote.

    Keyed/licensed providers (only if their API key is configured) come first,
    then the free broad-coverage source (yfinance), then fragile scraping
    (Investing) strictly as a last resort. This keeps the app resilient even
    with zero paid keys.
    """
    chain = []
    added = set()

    def add(inst):
        n = getattr(inst, "name", None)
        if n and n not in added:
            chain.append(inst)
            added.add(n)

    # Honour an explicit primary if its key is present.
    primary = os.environ.get("PRIMARY_PROVIDER", "").strip().lower()
    keyed = {
        "finnhub": ("FINNHUB_API_KEY", FinnhubProvider),
        "fmp": ("FMP_API_KEY", FMPProvider),
        "polygon": ("POLYGON_API_KEY", PolygonProvider),
        "alphavantage": ("ALPHAVANTAGE_API_KEY", AlphaVantageProvider),
        "twelvedata": ("TWELVEDATA_API_KEY", TwelveDataProvider),
        "marketstack": ("MARKETSTACK_API_KEY", MarketstackProvider),
    }
    if primary in keyed and os.environ.get(keyed[primary][0]):
        add(keyed[primary][1]())
    # Remaining keyed providers that actually have a key configured.
    for _name, (env, cls) in keyed.items():
        if os.environ.get(env):
            add(cls())
    # Free, broad-coverage source is always available.
    add(YFinanceProvider())
    # Fragile scraping — last resort only.
    add(InvestingProvider())
    return chain


def fetch_resilient(symbol: str) -> Optional[dict]:
    """Fetch a normalized quote by trying every source in the cascade.

    Never raises. Returns the first usable payload, or None if all sources
    failed (callers then fall back to stale cache / stored docs).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    errors = []
    for prov in _quote_chain():
        name = getattr(prov, "name", "provider")
        fragile = name in _FRAGILE_SOURCES
        if fragile and _breaker_open(name):
            continue
        try:
            d = prov.fetch(symbol)
            if d and d.get("price") is not None:
                d.setdefault("source", name)
                if fragile:
                    _breaker_record(name, True)
                return d
            if fragile:
                _breaker_record(name, False)
        except Exception as e:  # noqa: BLE001 - never crash on a provider error
            errors.append(f"{name}:{e}")
            if fragile:
                _breaker_record(name, False)
            continue
    if errors:
        logger.warning("fetch_resilient exhausted for %s (%s)", symbol, "; ".join(errors[:5]))
    return None


def search_resilient(query: str) -> list:
    """Search by trying every source in the cascade until one returns real matches.

    Never raises, and never invents a fake "literal ticker" result — if every
    source comes back empty (e.g. a provider is rate-limited), the caller gets
    an honest empty list instead of a made-up entry that looks like a match
    but isn't.
    """
    query = (query or "").strip()
    if not query:
        return []
    errors = []
    for prov in _quote_chain():
        name = getattr(prov, "name", "provider")
        fragile = name in _FRAGILE_SOURCES
        if fragile and _breaker_open(name):
            continue
        try:
            results = prov.search(query)
            if results:
                if fragile:
                    _breaker_record(name, True)
                return results
            if fragile:
                _breaker_record(name, False)
        except Exception as e:  # noqa: BLE001 - never crash on a provider error
            errors.append(f"{name}:{e}")
            if fragile:
                _breaker_record(name, False)
            continue
    if errors:
        logger.warning("search_resilient exhausted for %r (%s)", query, "; ".join(errors[:5]))
    return []


def get_provider() -> DataProvider:
    global _provider
    if _provider is None:
        primary = os.environ.get("PRIMARY_PROVIDER", "").strip().lower()
        
        # 1. Respect explicit PRIMARY_PROVIDER override
        if primary == "finnhub" and os.environ.get("FINNHUB_API_KEY"):
            _provider = FinnhubProvider()
        elif primary == "fmp" and os.environ.get("FMP_API_KEY"):
            _provider = FMPProvider()
        elif primary == "polygon" and os.environ.get("POLYGON_API_KEY"):
            _provider = PolygonProvider()
        elif primary == "alphavantage" and os.environ.get("ALPHAVANTAGE_API_KEY"):
            _provider = AlphaVantageProvider()
        elif primary == "twelvedata" and os.environ.get("TWELVEDATA_API_KEY"):
            _provider = TwelveDataProvider()
        elif primary == "marketstack" and os.environ.get("MARKETSTACK_API_KEY"):
            _provider = MarketstackProvider()
        elif primary == "investing":
            _provider = InvestingProvider()
            
        # 2. Fallback cascade prioritizing licensed data providers
        elif os.environ.get("FMP_API_KEY"):
            _provider = FMPProvider()
        elif os.environ.get("POLYGON_API_KEY"):
            _provider = PolygonProvider()
        elif os.environ.get("FINNHUB_API_KEY"):
            _provider = FinnhubProvider()
        elif os.environ.get("ALPHAVANTAGE_API_KEY"):
            _provider = AlphaVantageProvider()
        elif os.environ.get("TWELVEDATA_API_KEY"):
            _provider = TwelveDataProvider()
        elif os.environ.get("MARKETSTACK_API_KEY"):
            _provider = MarketstackProvider()
        else:
            # 3. Final fallback
            _provider = YFinanceProvider()
            
        logger.info("Initialized market-data provider: %s", getattr(_provider, "name", "unknown"))
    return _provider
