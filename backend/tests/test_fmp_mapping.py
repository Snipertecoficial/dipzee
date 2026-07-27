"""Unit tests for the FMP -> app-shape mapping (providers.fmp_*).

These mock FMP's HTTP layer (_FMP._get) and its key check, so they run offline
and guard the transform logic — especially the income/balance/cashflow
transposition, which is the riskiest part of the FMP migration.
"""
import providers


def _patch(monkeypatch, responses):
    """Patch the shared FMP provider to look configured and return canned
    payloads keyed by endpoint path."""
    monkeypatch.setattr(providers._FMP, "_key", lambda: "test-key")
    monkeypatch.setattr(providers._FMP, "_get", lambda path, params: responses.get(path))


def test_history_sorted_ascending_and_mapped(monkeypatch):
    _patch(monkeypatch, {"/historical-price-eod/full": [
        {"date": "2026-07-24", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        {"date": "2026-07-23", "open": 1, "high": 2, "low": 0.5, "close": 1.4, "volume": 90},
    ]})
    h = providers.fmp_history("AAPL", "1mo")
    assert [r["date"] for r in h] == ["2026-07-23", "2026-07-24"]  # ascending
    assert h[-1]["close"] == 1.5


def test_history_none_when_empty(monkeypatch):
    _patch(monkeypatch, {"/historical-price-eod/full": []})
    assert providers.fmp_history("AAPL", "1mo") is None


def test_target_consensus(monkeypatch):
    _patch(monkeypatch, {"/price-target-consensus": [{"targetConsensus": 342.11, "targetLow": 253, "targetHigh": 400}]})
    assert providers.fmp_target("AAPL") == 342.11


def test_fundamentals_transposed_to_line_item_rows(monkeypatch):
    _patch(monkeypatch, {
        "/income-statement": [
            {"date": "2025-09-27", "revenue": 400, "netIncome": 90, "eps": 6.0},
            {"date": "2024-09-28", "revenue": 380, "netIncome": 80, "eps": 5.5},
        ],
        "/balance-sheet-statement": [],
        "/cash-flow-statement": [],
        "/price-target-consensus": [{"targetConsensus": 342, "targetLow": 253, "targetHigh": 400}],
    })
    f = providers.fmp_fundamentals("AAPL")
    assert f["source"] == "fmp"
    rev = next(r for r in f["income_stmt"] if r["item"] == "Total Revenue")
    assert rev["2025-09-27"] == 400 and rev["2024-09-28"] == 380
    assert f["analyst_price_targets"] == {"low": 253, "mean": 342, "high": 400}


def test_fundamentals_none_when_all_empty(monkeypatch):
    _patch(monkeypatch, {"/income-statement": [], "/balance-sheet-statement": [], "/cash-flow-statement": []})
    assert providers.fmp_fundamentals("AAPL") is None


def test_screener_maps_and_unmapped_is_none(monkeypatch):
    _patch(monkeypatch, {"/biggest-gainers": [{"symbol": "ABC", "name": "ABC Inc", "price": 10, "changesPercentage": 5.5, "exchange": "NASDAQ"}]})
    s = providers.fmp_screener("day_gainers", 25)
    assert s["quotes"][0] == {"ticker": "ABC", "name": "ABC Inc", "price": 10, "change_pct": 5.5, "currency": "USD", "exchange": "NASDAQ", "market_cap": None}
    # A screen FMP doesn't map returns None so the caller falls back to yfinance.
    assert providers.fmp_screener("crypto", 25) is None
