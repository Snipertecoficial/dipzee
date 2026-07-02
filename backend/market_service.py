"""Market-data service built on yfinance (blocking calls run in a threadpool).

Every function here is synchronous and is invoked through
``market_cache.cached`` which adds TTL caching, exponential-backoff retries and
a stale-on-error fallback. Keep these functions pure data-fetch + normalize.

NOTE (honesty): yfinance uses Yahoo's public/undocumented endpoints and is
intended for personal/research use. For commercial production, swap the loaders
below for a licensed provider (FMP / Finnhub / Polygon / Twelve Data). The
router and cache layers stay identical.
"""
import logging
import math
from typing import Optional

import pandas as pd
import yfinance as yf

from providers import get_provider, normalize_dividend_yield, _derive_exchange

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# JSON-safe conversion helpers
# --------------------------------------------------------------------------- #
def _scalar(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    if hasattr(v, "item"):  # numpy scalar
        try:
            v = v.item()
        except Exception:  # noqa: BLE001
            return str(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _records(df: Optional[pd.DataFrame]) -> list:
    """Convert a DataFrame to a list of JSON-safe records (index included)."""
    if df is None or not hasattr(df, "empty") or df.empty:
        return []
    d = df.copy()
    d = d.reset_index()
    d.columns = [str(c) for c in d.columns]
    out = []
    for _, row in d.iterrows():
        out.append({k: _scalar(row[k]) for k in d.columns})
    return out


def _statement(df: Optional[pd.DataFrame]) -> list:
    """Financial statements: columns are period dates, index are line items."""
    if df is None or not hasattr(df, "empty") or df.empty:
        return []
    d = df.copy()
    d.columns = [c.date().isoformat() if hasattr(c, "date") else str(c) for c in d.columns]
    d = d.reset_index()
    d = d.rename(columns={d.columns[0]: "item"})
    d.columns = [str(c) for c in d.columns]
    out = []
    for _, row in d.iterrows():
        out.append({k: _scalar(row[k]) for k in d.columns})
    return out


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def quote(symbol: str) -> Optional[dict]:
    """Real-time quote. Primary: configured provider (Finnhub). Fallback: yfinance."""
    symbol = symbol.strip().upper()

    # Primary provider (reliable, keyed).
    try:
        prov = get_provider()
        d = prov.fetch(symbol)
        if d and d.get("price"):
            d.setdefault("source", getattr(prov, "name", "provider"))
            # Backfill 52-week range from yfinance when the primary omits it
            # (the range feeds the Opportunity Score, so it must be populated).
            if d.get("low_52w") is None or d.get("high_52w") is None:
                try:
                    fi = dict(yf.Ticker(symbol).fast_info or {})
                    if d.get("low_52w") is None:
                        d["low_52w"] = fi.get("year_low")
                    if d.get("high_52w") is None:
                        d["high_52w"] = fi.get("year_high")
                except Exception as e:  # noqa: BLE001
                    logger.warning("52w backfill failed for %s: %s", symbol, e)
            return d
    except Exception as e:  # noqa: BLE001
        logger.warning("provider quote failed for %s: %s", symbol, e)

    # Fallback: yfinance fast_info + info.
    t = yf.Ticker(symbol)
    fi = {}
    try:
        fi = dict(t.fast_info or {})
    except Exception:  # noqa: BLE001
        fi = {}
    info = {}
    try:
        info = t.info or {}
    except Exception:  # noqa: BLE001
        info = {}

    price = fi.get("last_price") or info.get("currentPrice") or info.get("regularMarketPrice")
    low = fi.get("year_low") or info.get("fiftyTwoWeekLow")
    high = fi.get("year_high") or info.get("fiftyTwoWeekHigh")
    if price is None and low is None and high is None:
        return None
    prev = fi.get("previous_close") or info.get("regularMarketPreviousClose")
    change_pct = None
    if price and prev:
        try:
            change_pct = round((price - prev) / prev * 100, 2)
        except Exception:  # noqa: BLE001
            change_pct = None
    return {
        "ticker": symbol,
        "exchange": _derive_exchange(symbol, info),
        "name": info.get("longName") or info.get("shortName") or symbol,
        "currency": fi.get("currency") or info.get("currency") or "USD",
        "price": price,
        "low_52w": low,
        "high_52w": high,
        "target_mean": info.get("targetMeanPrice"),
        "dividend_yield": normalize_dividend_yield(info),
        "sector": info.get("sector"),
        "change_pct": change_pct,
        "prev_close": prev,
        "market_cap": fi.get("market_cap") or info.get("marketCap"),
        "source": "yfinance",
    }


def history(symbol: str, period: str = "1mo", interval: str = "1d") -> list:
    symbol = symbol.strip().upper()
    df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return []
    df = df.rename(columns={c: c.lower().replace(" ", "_") for c in df.columns})
    return _records(df)


def batch(symbols: list, period: str = "1mo", interval: str = "1d") -> dict:
    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return {}
    data = yf.download(
        symbols, period=period, interval=interval,
        group_by="ticker", auto_adjust=False, progress=False, threads=True,
    )
    out = {}
    if data is None or data.empty:
        return {s: [] for s in symbols}
    # Multi-symbol => MultiIndex columns (symbol, field). Single symbol => flat.
    if len(symbols) == 1:
        out[symbols[0]] = _records(data.rename(columns={c: str(c).lower() for c in data.columns}))
        return out
    for s in symbols:
        try:
            sub = data[s].dropna(how="all")
            sub = sub.rename(columns={c: str(c).lower() for c in sub.columns})
            out[s] = _records(sub)
        except Exception:  # noqa: BLE001
            out[s] = []
    return out


def market_summary(market: str = "US") -> dict:
    m = yf.Market(market)
    payload = {}
    for attr in ("summary", "status"):
        try:
            val = getattr(m, attr)
            if val is not None:
                # Some versions expose DataFrames; normalize to JSON-safe.
                if isinstance(val, pd.DataFrame):
                    payload[attr] = _records(val)
                else:
                    payload[attr] = val
        except Exception as e:  # noqa: BLE001
            logger.warning("market %s.%s failed: %s", market, attr, e)
    return payload or {"market": market, "available": False}


def search(query: str) -> dict:
    query = query.strip()
    quotes, news = [], []
    try:
        s = yf.Search(query, max_results=10, news_count=6)
        for q in (s.quotes or []):
            sym = q.get("symbol")
            if not sym:
                continue
            quotes.append({
                "ticker": sym,
                "name": q.get("longname") or q.get("shortname") or sym,
                "exchange": q.get("exchange") or "",
                "type": q.get("quoteType") or "",
            })
        for n in (s.news or []):
            news.append({
                "title": n.get("title"),
                "publisher": n.get("publisher"),
                "link": n.get("link"),
                "providerPublishTime": n.get("providerPublishTime"),
            })
    except Exception as e:  # noqa: BLE001
        logger.warning("yfinance search failed for %s: %s", query, e)

    if not quotes:
        # Fallback to the configured provider's search (Finnhub).
        try:
            for r in (get_provider().search(query) or []):
                quotes.append({"ticker": r["ticker"], "name": r.get("name") or r["ticker"], "exchange": r.get("exchange") or "", "type": ""})
        except Exception:  # noqa: BLE001
            pass
    return {"quotes": quotes, "news": news}


def fundamentals(symbol: str) -> dict:
    symbol = symbol.strip().upper()
    t = yf.Ticker(symbol)
    out = {"ticker": symbol}

    def _safe(name, fn):
        try:
            out[name] = fn()
        except Exception as e:  # noqa: BLE001
            logger.warning("fundamentals %s.%s failed: %s", symbol, name, e)
            out[name] = [] if name != "analyst_price_targets" and name != "calendar" else {}

    _safe("income_stmt", lambda: _statement(t.income_stmt))
    _safe("balance_sheet", lambda: _statement(t.balance_sheet))
    _safe("cashflow", lambda: _statement(t.cashflow))

    # calendar can be a dict (newer) or DataFrame (older).
    def _calendar():
        cal = t.calendar
        if isinstance(cal, pd.DataFrame):
            return _records(cal)
        if isinstance(cal, dict):
            return {k: _scalar(v) if not isinstance(v, list) else [_scalar(x) for x in v] for k, v in cal.items()}
        return {}
    _safe("calendar", _calendar)

    # analyst_price_targets can be a dict or DataFrame depending on version.
    def _targets():
        apt = t.analyst_price_targets
        if isinstance(apt, dict):
            return {k: _scalar(v) for k, v in apt.items()}
        if isinstance(apt, pd.DataFrame):
            return _records(apt)
        return {}
    _safe("analyst_price_targets", _targets)

    return out


def options(symbol: str, expiration: Optional[str] = None) -> dict:
    symbol = symbol.strip().upper()
    t = yf.Ticker(symbol)
    dates = []
    try:
        dates = list(t.options or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("options dates failed for %s: %s", symbol, e)
    result = {"ticker": symbol, "expirations": dates}
    if expiration and expiration in dates:
        try:
            chain = t.option_chain(expiration)
            result["expiration"] = expiration
            result["calls"] = _records(chain.calls)
            result["puts"] = _records(chain.puts)
        except Exception as e:  # noqa: BLE001
            logger.warning("option_chain failed for %s %s: %s", symbol, expiration, e)
            result["calls"] = []
            result["puts"] = []
    return result


PREDEFINED_SCREENS = {
    "day_gainers", "day_losers", "most_actives", "aggressive_small_caps",
    "growth_technology_stocks", "small_cap_gainers", "undervalued_growth_stocks",
    "undervalued_large_caps", "most_shorted_stocks", "portfolio_anchors",
}


def screener(screen_type: str = "day_gainers", count: int = 25) -> dict:
    screen_type = (screen_type or "day_gainers").strip()
    try:
        body = yf.screen(screen_type, count=count)
    except TypeError:
        body = yf.screen(screen_type)
    quotes = []
    raw = (body or {}).get("quotes", []) if isinstance(body, dict) else []
    for q in raw:
        quotes.append({
            "ticker": q.get("symbol"),
            "name": q.get("longName") or q.get("shortName") or q.get("symbol"),
            "price": q.get("regularMarketPrice"),
            "change_pct": q.get("regularMarketChangePercent"),
            "currency": q.get("currency"),
            "exchange": q.get("fullExchangeName") or q.get("exchange"),
            "market_cap": q.get("marketCap"),
        })
    return {"type": screen_type, "count": len(quotes), "quotes": quotes}
