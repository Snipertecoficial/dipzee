"""Unit tests for LSE ingestion wiring (no SDK, no network).

The high-level `lse_service` fetchers are monkeypatched to return canned rows,
so this exercises the normalize -> upsert -> run-summary path against the fake
in-memory DB, plus the budget-stop and not-configured behaviors.
"""
import asyncio

import pytest

import lse_ingest
import lse_service as lse
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(lse_ingest, "db", db)
    return db


def _canned(monkeypatch):
    async def candles(symbol, timeframe, limit=None):
        return [{"date": "2026-07-27", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100}]
    async def dividends(symbol):
        return [{"exDate": "2026-06-14", "amount": 0.49}]
    async def splits(symbol):
        return [{"date": "2024-06-10", "numerator": 10, "denominator": 1}]
    async def fundamentals(symbol):
        return {"pe": 30}
    monkeypatch.setattr(lse, "candles", candles)
    monkeypatch.setattr(lse, "dividends", dividends)
    monkeypatch.setattr(lse, "splits", splits)
    monkeypatch.setattr(lse, "fundamentals", fundamentals)
    monkeypatch.setattr(lse, "is_configured", lambda: True)


def test_ingest_symbol_upserts_all_sources(fake_db, monkeypatch):
    _canned(monkeypatch)
    r = _run(lse_ingest.ingest_symbol("aapl"))
    assert r == {"symbol": "AAPL", "candles": 1, "dividends": 1, "splits": 1, "fundamentals": 1}
    assert _run(fake_db.lse_candles.find_one({"symbol": "AAPL"}))["close"] == 1.5
    assert _run(fake_db.lse_dividends.find_one({"symbol": "AAPL"}))["ex_date"] == "2026-06-14"
    assert _run(fake_db.lse_fundamentals.find_one({"symbol": "AAPL"}))["data"] == {"pe": 30}


def test_run_ingestion_records_summary(fake_db, monkeypatch):
    _canned(monkeypatch)
    summary = _run(lse_ingest.run_ingestion(symbols=["AAPL", "MSFT"]))
    assert summary["symbols_done"] == 2 and summary["candles"] == 2
    assert summary["budget_stopped"] is False
    logged = _run(lse_ingest.last_ingest())
    assert logged["symbols_done"] == 2


def test_run_ingestion_stops_on_budget(fake_db, monkeypatch):
    _canned(monkeypatch)
    # First symbol ingests; second raises budget -> run stops and is flagged.
    calls = {"n": 0}
    async def candles(symbol, timeframe, limit=None):
        calls["n"] += 1
        if calls["n"] > 1:
            raise lse.LSEBudgetError("cap")
        return [{"date": "2026-07-27", "c": 1.5}]
    monkeypatch.setattr(lse, "candles", candles)
    summary = _run(lse_ingest.run_ingestion(symbols=["AAPL", "MSFT", "GOOG"]))
    assert summary["budget_stopped"] is True
    assert summary["symbols_done"] == 1


def test_run_ingestion_noop_when_unconfigured(fake_db, monkeypatch):
    monkeypatch.setattr(lse, "is_configured", lambda: False)
    summary = _run(lse_ingest.run_ingestion(symbols=["AAPL"]))
    assert summary["configured"] is False and summary["symbols_done"] == 0
