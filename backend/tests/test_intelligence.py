"""Unit tests for the intelligence agents (L3).

Offline: deterministic context builders are tested directly; the LLM composers
are tested only for output sanitization via a monkeypatched `_generate` (no
provider/network). Options-flow summary is tested with a monkeypatched LSE.
"""
import asyncio

import pytest

from intelligence import agents
import lse_service as lse
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


# --- net_impact_from_events (pure) ------------------------------------------ #

def test_net_impact_confidence_weighted():
    events = [
        {"headline": "a", "event_type": "macro",
         "affected": [{"symbol": "XOM", "impact": 0.6, "confidence": 0.8, "via": ["commodity"]}]},
        {"headline": "b", "event_type": "analyst",
         "affected": [{"symbol": "XOM", "impact": -0.2, "confidence": 0.2}]},
        {"headline": "c", "affected": [{"symbol": "JPM", "impact": 0.5, "confidence": 0.5}]},
    ]
    out = agents.net_impact_from_events(events, "XOM")
    # (0.6*0.8 + -0.2*0.2) / (0.8+0.2) = (0.48 - 0.04)/1.0 = 0.44
    assert out["net_impact"] == pytest.approx(0.44)
    assert out["event_count"] == 2


def test_net_impact_empty():
    assert agents.net_impact_from_events([], "XOM") == {"net_impact": 0.0, "event_count": 0, "contributors": []}


# --- options-flow summary --------------------------------------------------- #

def test_options_flow_unconfigured(monkeypatch):
    monkeypatch.setattr(lse, "is_configured", lambda: False)
    out = _run(agents.summarize_options_flow("AAPL"))
    assert out == {"available": False, "reason": "lse_not_configured"}


def test_options_flow_skew(monkeypatch):
    monkeypatch.setattr(lse, "is_configured", lambda: True)
    async def flow(sym):
        return [
            {"type": "call", "premium": 300},
            {"type": "call", "premium": 100},
            {"type": "put", "premium": 100},
        ]
    monkeypatch.setattr(lse, "options_flow", flow)
    out = _run(agents.summarize_options_flow("AAPL"))
    assert out["available"] and out["prints"] == 3
    assert out["call_premium"] == 400 and out["put_premium"] == 100
    assert out["call_put_skew"] == pytest.approx(0.6)  # (400-100)/500


def test_options_flow_budget_degrades(monkeypatch):
    monkeypatch.setattr(lse, "is_configured", lambda: True)
    async def flow(sym):
        raise lse.LSEBudgetError("cap")
    monkeypatch.setattr(lse, "options_flow", flow)
    out = _run(agents.summarize_options_flow("AAPL"))
    assert out == {"available": False, "reason": "budget"}


# --- macro snapshot (fakedb) ------------------------------------------------ #

def test_macro_snapshot_tallies_moves():
    db = FakeDB()
    _run(db.market_events.insert_one({
        "id": "e1", "headline": "Oil up", "enriched_at": "2026-07-27T00:00:00+00:00",
        "entities": {"commodities": [{"id": "crude_oil", "move": "up"}], "macro": []},
        "affected": []}))
    _run(db.market_events.insert_one({
        "id": "e2", "headline": "Fed hikes", "enriched_at": "2026-07-27T01:00:00+00:00",
        "entities": {"commodities": [], "macro": [{"id": "interest_rates", "move": "up"}]},
        "affected": []}))
    snap = _run(agents.macro_snapshot(db))
    by = {f["id"]: f for f in snap["factors"]}
    assert by["crude_oil"]["net_move"] == "up"
    assert by["interest_rates"]["up"] == 1


# --- LLM composer output sanitization (monkeypatched _generate) ------------- #

def test_explain_asset_sanitizes(monkeypatch):
    async def fake_gen(system, user):
        return {"headline": "h", "summary": "s", "drivers": ["d1", "d2"],
                "macro_context": "m", "stance": "BOGUS", "watch": ["w1", "w2", "w3", "w4"],
                "confidence": 250}
    monkeypatch.setattr(agents, "_generate", fake_gen)
    out = _run(agents.explain_asset({"net_impact": 0.3}, "en"))
    assert out["stance"] == "watch"          # invalid -> default
    assert out["confidence"] == 100          # clamped
    assert len(out["watch"]) == 3            # capped
    assert out["net_impact"] == 0.3          # passed through from context


def test_explain_macro_shapes(monkeypatch):
    async def fake_gen(system, user):
        return {"summary": "s", "favored_sectors": ["Energy"], "pressured_sectors": ["Utilities"],
                "watch": ["CPI print"]}
    monkeypatch.setattr(agents, "_generate", fake_gen)
    out = _run(agents.explain_macro({"factors": []}, "pt"))
    assert out["favored_sectors"] == ["Energy"] and out["pressured_sectors"] == ["Utilities"]
