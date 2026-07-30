"""London Strategic Edge (LSE) market-data service.

A thin, async-friendly wrapper over the official *synchronous* `lse-data` SDK
(``from lse import LSE``). It exists so the rest of the app treats LSE like any
other data source (mirrors the ``providers.py`` pattern) while three things are
handled here, in one place:

1. **Lazy, resilient client.** The SDK and key are optional — nothing imports at
   module load. If ``LSE_API_KEY`` is unset or the package isn't installed, the
   service reports "not configured" instead of crashing the app.

2. **Off-thread execution.** The SDK is blocking (HTTP + WebSocket). Every call
   is dispatched via ``asyncio.to_thread`` so it never stalls the FastAPI event
   loop.

3. **Budget guard.** LSE shares one allowance across stream/download and caps an
   hourly *export budget*. We never risk overrunning it: a call is refused
   (``LSEBudgetError``) when either (a) our own per-process hourly call cap is
   reached, or (b) the vault reports the remaining export budget below a small
   reserve. The vault reading is cached briefly to avoid a meta-cost per call.

Security: the key is server-side only (``.env``, gitignored). We use the
official authenticated API openly — no scraping, no evasion.
"""
import asyncio
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


# Hard local ceiling on LSE calls per rolling hour (enforced even when the
# vault-usage shape can't be parsed) — the always-on backstop against runaway.
LSE_MAX_CALLS_PER_HOUR = _env_int("LSE_MAX_CALLS_PER_HOUR", 500)
# Refuse a call when the vault's remaining export budget drops below this
# fraction, keeping headroom for critical/ad-hoc calls.
LSE_BUDGET_RESERVE = _env_float("LSE_BUDGET_RESERVE", 0.05)
# Cache the vault-usage reading this many seconds (avoid a meta-call per call).
_VAULT_TTL = 60


class LSEError(Exception):
    """Base error for the LSE service layer."""


class LSENotConfigured(LSEError):
    """Raised when the API key or the `lse-data` SDK is unavailable."""


class LSEBudgetError(LSEError):
    """Raised when a call would risk exceeding the LSE budget/allowance."""


# --------------------------------------------------------------------------- #
# Client (lazy singleton) + budget state
# --------------------------------------------------------------------------- #
_client = None
_local_calls: deque = deque()          # monotonic timestamps of recent calls
_vault_cache = {"at": 0.0, "usage": None}


def is_configured() -> bool:
    """True when an API key is present (the SDK import is checked lazily)."""
    return bool(os.environ.get("LSE_API_KEY"))


def client_raw_exposure_enabled() -> bool:
    """Whether raw LSE-derived data may be surfaced to clients.

    Rights were granted by LSE, so this is an operational toggle (default off
    until the client surface in L6 exists — there is nothing to expose yet).
    """
    return os.environ.get("LSE_CLIENT_RAW_EXPOSURE", "off").strip().lower() in ("on", "1", "true", "yes")


def _get_client():
    global _client
    if _client is None:
        if not is_configured():
            raise LSENotConfigured("LSE_API_KEY is not set")
        try:
            from lse import LSE  # noqa: WPS433 (lazy, optional dependency)
        except ImportError as e:  # pragma: no cover - only when SDK missing
            raise LSENotConfigured(f"lse-data SDK not installed: {e}")
        _client = LSE(api_key=os.environ["LSE_API_KEY"])
        logger.info("[lse] client initialized")
    return _client


# --------------------------------------------------------------------------- #
# Budget guard (pure logic — unit-tested without the SDK)
# --------------------------------------------------------------------------- #
def _prune_local(now: float) -> None:
    cutoff = now - 3600
    while _local_calls and _local_calls[0] < cutoff:
        _local_calls.popleft()


def local_calls_last_hour() -> int:
    """How many LSE calls this process made in the trailing hour (admin view)."""
    _prune_local(time.time())
    return len(_local_calls)


def record_call() -> None:
    """Record one synchronous LSE call against the rolling hourly budget.

    Mirrors what the async ``_call`` appends, so the synchronous provider path
    (``providers.LSEProvider``) shares the very same allowance counter."""
    _local_calls.append(time.time())


def under_local_budget() -> bool:
    """True when the process still has hourly headroom for a synchronous call.

    The provider cascade needs a *non-raising, non-async* budget check so it can
    silently fall through to the next source instead of blocking. We keep a small
    reserve (``LSE_BUDGET_RESERVE``) of the local cap for critical/ad-hoc calls;
    the vault probe is intentionally skipped here (the local hourly cap is the
    always-on backstop, and a per-call network probe would defeat the purpose)."""
    _prune_local(time.time())
    ceiling = int(LSE_MAX_CALLS_PER_HOUR * (1.0 - LSE_BUDGET_RESERVE))
    return len(_local_calls) < max(1, ceiling)


def parse_remaining_fraction(usage) -> Optional[float]:
    """Best-effort remaining-budget fraction in [0, 1] from a vault-usage payload.

    The exact shape isn't contractual, so this is defensive: it looks for a
    node carrying remaining/limit (or used/limit) under a few likely keys, then
    the top level. Returns None when nothing usable is found (caller then relies
    on the local hourly cap alone rather than blocking blindly)."""
    def frac(node) -> Optional[float]:
        if not isinstance(node, dict):
            return None
        limit = node.get("limit") or node.get("budget") or node.get("total") or node.get("allowance")
        remaining = node.get("remaining")
        used = node.get("used")
        try:
            if remaining is not None and limit:
                return max(0.0, min(1.0, float(remaining) / float(limit)))
            if used is not None and limit:
                return max(0.0, min(1.0, 1.0 - float(used) / float(limit)))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return None

    if not isinstance(usage, dict):
        return None
    for key in ("export_budget", "export", "budget", "hourly", "usage"):
        f = frac(usage.get(key))
        if f is not None:
            return f
    return frac(usage)


async def _vault_usage(force: bool = False):
    """Return the vault-usage payload, cached for `_VAULT_TTL` seconds. Never
    raises — returns the last known reading (or None) on failure."""
    now = time.time()
    if not force and _vault_cache["usage"] is not None and now - _vault_cache["at"] < _VAULT_TTL:
        return _vault_cache["usage"]
    client = _get_client()
    getter = getattr(client, "GET", None) or getattr(client, "get", None)
    if getter is None:
        return _vault_cache["usage"]
    try:
        usage = await asyncio.to_thread(getter, "/vault/usage")
    except Exception as e:  # noqa: BLE001 - never crash on a usage probe
        logger.warning("[lse] vault usage probe failed: %s", e)
        return _vault_cache["usage"]
    _vault_cache["usage"] = usage
    _vault_cache["at"] = now
    return usage


async def vault_usage() -> Optional[dict]:
    """Public accessor for the admin panel (cached)."""
    if not is_configured():
        return None
    return await _vault_usage()


async def _guard() -> None:
    """Raise LSEBudgetError if making a call now would risk the budget."""
    now = time.time()
    _prune_local(now)
    if len(_local_calls) >= LSE_MAX_CALLS_PER_HOUR:
        raise LSEBudgetError(f"local hourly LSE call cap reached ({LSE_MAX_CALLS_PER_HOUR}/h)")
    frac = parse_remaining_fraction(await _vault_usage())
    if frac is not None and frac < LSE_BUDGET_RESERVE:
        raise LSEBudgetError(f"LSE export budget nearly exhausted (remaining={frac:.1%})")


async def _call(method: str, *args, **kwargs):
    """Budget-guarded, thread-offloaded SDK call. Raises LSEBudgetError /
    LSENotConfigured / whatever the SDK raises (callers decide how to degrade)."""
    await _guard()
    client = _get_client()
    fn = getattr(client, method, None)
    if fn is None:
        raise LSEError(f"LSE SDK has no method '{method}'")
    _local_calls.append(time.time())
    return await asyncio.to_thread(lambda: fn(*args, **kwargs))


# --------------------------------------------------------------------------- #
# Public data methods (thin pass-throughs over the SDK)
# --------------------------------------------------------------------------- #
async def candles(symbol: str, timeframe: str = "1d", start=None, end=None, limit=None):
    return await _call("candles", symbol, timeframe, start=start, end=end, limit=limit)


async def fundamentals(symbol: str):
    return await _call("fundamentals", symbol)


async def company_profiles(symbol: str):
    return await _call("company_profiles", symbol)


async def dividends(symbol: str):
    return await _call("dividends", symbol)


async def splits(symbol: str):
    return await _call("splits", symbol)


async def options(ticker_or_name: str, type: Optional[str] = None, max_dte: Optional[int] = None):
    return await _call("options", ticker_or_name, type=type, max_dte=max_dte)


async def options_flow(symbol: str, min_premium=None, start=None, end=None):
    return await _call("options_flow", symbol, min_premium=min_premium, start=start, end=end)


async def economics(series_name: str):
    return await _call("economics", series_name)


async def series(series_code: str, start=None):
    return await _call("series", series_code, start=start)


async def economic_calendar(region: Optional[str] = None, start=None):
    return await _call("economic_calendar", region=region, start=start)


async def insider_trades(symbol: str, type: Optional[str] = None):
    return await _call("insider_trades", symbol, type=type)


async def catalog(category: Optional[str] = None):
    return await _call("catalog", category) if category else await _call("catalog")


# --------------------------------------------------------------------------- #
# Normalization helpers (SDK dict -> our stored shape)
# --------------------------------------------------------------------------- #
def _first(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _iso(value) -> Optional[str]:
    """Coerce a date/datetime/epoch/string into an ISO string (UTC for epochs)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        # Heuristic: ms vs s epoch.
        ts = value / 1000.0 if value > 1e12 else float(value)
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    return str(value)


def normalize_candle(symbol: str, timeframe: str, row: dict) -> Optional[dict]:
    if not isinstance(row, dict):
        return None
    ts = _iso(_first(row, "timestamp", "datetime", "date", "time", "t"))
    close = _first(row, "close", "c")
    if ts is None or close is None:
        return None
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "ts": ts,
        "open": _first(row, "open", "o"),
        "high": _first(row, "high", "h"),
        "low": _first(row, "low", "l"),
        "close": close,
        "volume": _first(row, "volume", "v"),
        "source": "lse",
    }


def normalize_dividend(symbol: str, row: dict) -> Optional[dict]:
    if not isinstance(row, dict):
        return None
    ex_date = _iso(_first(row, "ex_date", "exDate", "date", "ex_dividend_date"))
    if ex_date is None:
        return None
    return {
        "symbol": symbol,
        "ex_date": ex_date,
        "amount": _first(row, "amount", "value", "cash_amount", "dividend"),
        "pay_date": _iso(_first(row, "pay_date", "payDate", "payment_date")),
        "source": "lse",
    }


def normalize_split(symbol: str, row: dict) -> Optional[dict]:
    if not isinstance(row, dict):
        return None
    date = _iso(_first(row, "date", "ex_date", "effective_date"))
    if date is None:
        return None
    return {
        "symbol": symbol,
        "date": date,
        "ratio": _first(row, "ratio", "split_ratio", "value"),
        "numerator": _first(row, "numerator", "to"),
        "denominator": _first(row, "denominator", "from"),
        "source": "lse",
    }
