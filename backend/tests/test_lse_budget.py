"""Unit tests for the LSE service budget guard + normalization.

These never import the `lse-data` SDK or hit the network: the vault-usage probe
is monkeypatched, and the pure helpers (budget parsing, normalization) run
offline. They guard the two riskiest bits: never overrunning the budget, and
faithfully mapping the SDK's loosely-shaped rows into our stored docs.
"""
import asyncio
import time

import pytest

import lse_service as lse


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _reset_state():
    """Each test starts with an empty call window and clean vault cache."""
    lse._local_calls.clear()
    lse._vault_cache["at"] = 0.0
    lse._vault_cache["usage"] = None
    yield
    lse._local_calls.clear()


# --- parse_remaining_fraction: defensive across shapes ---------------------- #

def test_parse_remaining_over_limit():
    assert lse.parse_remaining_fraction({"remaining": 25, "limit": 100}) == 0.25


def test_parse_used_over_limit():
    assert lse.parse_remaining_fraction({"used": 90, "limit": 100}) == pytest.approx(0.10)


def test_parse_nested_export_budget():
    assert lse.parse_remaining_fraction({"export_budget": {"remaining": 5, "limit": 50}}) == pytest.approx(0.10)


def test_parse_clamped_and_unparseable():
    # Over-limit remaining clamps to 1.0; junk yields None (caller uses local cap).
    assert lse.parse_remaining_fraction({"remaining": 200, "limit": 100}) == 1.0
    assert lse.parse_remaining_fraction({"foo": "bar"}) is None
    assert lse.parse_remaining_fraction(None) is None


# --- _guard: the two independent stop conditions ---------------------------- #

def test_guard_blocks_when_local_cap_reached(monkeypatch):
    monkeypatch.setattr(lse, "LSE_MAX_CALLS_PER_HOUR", 3)
    # Vault probe returns plenty of budget, so only the local cap can trip.
    async def _plenty(force=False):
        return {"remaining": 100, "limit": 100}
    monkeypatch.setattr(lse, "_vault_usage", _plenty)
    now = time.time()
    lse._local_calls.extend([now, now, now])  # exactly at the cap
    with pytest.raises(lse.LSEBudgetError):
        _run(lse._guard())


def test_guard_blocks_when_vault_budget_low(monkeypatch):
    async def _low(force=False):
        return {"remaining": 1, "limit": 100}  # 1% < 5% reserve
    monkeypatch.setattr(lse, "_vault_usage", _low)
    with pytest.raises(lse.LSEBudgetError):
        _run(lse._guard())


def test_guard_allows_when_budget_healthy(monkeypatch):
    async def _ok(force=False):
        return {"remaining": 80, "limit": 100}
    monkeypatch.setattr(lse, "_vault_usage", _ok)
    _run(lse._guard())  # must not raise


def test_guard_allows_when_vault_unparseable(monkeypatch):
    # Unknown shape -> fall back to the local cap alone, don't block blindly.
    async def _unknown(force=False):
        return {"weird": "payload"}
    monkeypatch.setattr(lse, "_vault_usage", _unknown)
    _run(lse._guard())  # must not raise


def test_local_calls_last_hour_prunes_old():
    lse._local_calls.append(time.time() - 7200)  # 2h ago -> pruned
    lse._local_calls.append(time.time())          # now -> kept
    assert lse.local_calls_last_hour() == 1


# --- normalization: loose SDK rows -> stored docs --------------------------- #

def test_normalize_candle_maps_and_requires_close_and_ts():
    row = {"date": "2026-07-27", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100}
    d = lse.normalize_candle("AAPL", "1d", row)
    assert d["symbol"] == "AAPL" and d["timeframe"] == "1d"
    assert d["ts"] == "2026-07-27" and d["close"] == 1.5 and d["open"] == 1 and d["volume"] == 100
    # No close -> unusable row -> None.
    assert lse.normalize_candle("AAPL", "1d", {"date": "2026-07-27"}) is None
    assert lse.normalize_candle("AAPL", "1d", "not-a-dict") is None


def test_normalize_dividend_requires_ex_date():
    d = lse.normalize_dividend("KO", {"exDate": "2026-06-14", "amount": 0.49})
    assert d == {"symbol": "KO", "ex_date": "2026-06-14", "amount": 0.49, "pay_date": None, "source": "lse"}
    assert lse.normalize_dividend("KO", {"amount": 0.49}) is None


def test_normalize_split_maps_ratio():
    d = lse.normalize_split("NVDA", {"date": "2024-06-10", "numerator": 10, "denominator": 1})
    assert d["symbol"] == "NVDA" and d["date"] == "2024-06-10"
    assert d["numerator"] == 10 and d["denominator"] == 1
    assert lse.normalize_split("NVDA", {"ratio": 10}) is None
