"""Unit tests for market memory (L4) — offline.

Vectorization, cosine/kNN, forward-return/outcome from stored candles, indexing,
and similarity retrieval, all against pure functions + the fake in-memory DB.
"""
import asyncio

import pytest

import memory_service as mem
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


def _event(eid, commodity_move=None, sector=None, impact=0.0, sentiment=0.0, date="2026-07-01"):
    ent = {"commodities": [], "macro": []}
    if commodity_move:
        ent["commodities"] = [{"id": "crude_oil", "move": commodity_move}]
    affected = [{"symbol": "XOM", "impact": impact, "sector": sector, "confidence": 0.8}] if sector else []
    return {"id": eid, "headline": f"event {eid}", "datetime": date, "event_type": "macro",
            "sentiment": sentiment, "entities": ent, "affected": affected}


# --- vectorization ---------------------------------------------------------- #

def test_vector_dim_and_factor_encoding():
    v = mem.event_vector(_event("e1", commodity_move="up"))
    assert len(v) == mem.VECTOR_DIM
    assert v[0] == 1.0  # crude_oil is the first factor, move up


def test_vector_sector_impact_dim():
    v = mem.event_vector(_event("e1", sector="Energy", impact=0.6))
    energy_idx = len(mem._FACTORS) + 1 + len(mem._EVENT_TYPES) + mem._SECTORS.index("Energy")
    assert v[energy_idx] == pytest.approx(0.6)


# --- cosine + knn ----------------------------------------------------------- #

def test_cosine_identity_and_zero():
    assert mem.cosine([1, 0, 1], [1, 0, 1]) == pytest.approx(1.0)
    assert mem.cosine([1, 0], [0, 1]) == 0.0
    assert mem.cosine([0, 0], [1, 1]) == 0.0


def test_knn_ranks_and_filters():
    q = [1.0, 0.0, 0.0]
    cands = [
        {"id": "a", "vector": [1.0, 0.0, 0.0]},   # sim 1.0
        {"id": "b", "vector": [0.0, 1.0, 0.0]},   # sim 0.0 -> filtered by min_sim
        {"id": "c", "vector": [0.8, 0.2, 0.0]},   # sim ~0.97
    ]
    out = mem.knn(q, cands, k=2, min_sim=0.1)
    assert [n["id"] for n in out] == ["a", "c"]


# --- outcomes from candles -------------------------------------------------- #

@pytest.fixture
def db_with_candles():
    db = FakeDB()
    # 7 ascending daily closes from the event date; +5 trading days => index 5.
    closes = [100, 101, 102, 103, 104, 110, 111]
    for i, c in enumerate(closes):
        _run(db.lse_candles.insert_one({"symbol": "XOM", "timeframe": "1d",
                                        "ts": f"2026-07-0{i+1}", "close": c}))
    return db


def test_forward_return(db_with_candles):
    r = _run(mem._forward_return(db_with_candles, "XOM", "2026-07-01", 5))
    assert r == pytest.approx(10.0)  # (110-100)/100


def test_forward_return_insufficient_history(db_with_candles):
    assert _run(mem._forward_return(db_with_candles, "XOM", "2026-07-01", 50)) is None


def test_compute_outcome_resolved(db_with_candles):
    ev = _event("e1", sector="Energy", impact=0.6, date="2026-07-01")
    out = _run(mem.compute_outcome(db_with_candles, ev, horizon=5))
    assert out["status"] == "resolved" and out["avg_return"] == pytest.approx(10.0)


def test_compute_outcome_pending_without_history():
    ev = _event("e1", sector="Energy", impact=0.6, date="2026-07-01")
    out = _run(mem.compute_outcome(FakeDB(), ev, horizon=5))
    assert out["status"] == "pending" and out["avg_return"] is None


# --- indexing + retrieval --------------------------------------------------- #

def test_index_and_similar(db_with_candles):
    db = db_with_candles
    # Two crude-oil-up events (similar) + one unrelated, all in market_events.
    for e in [_event("e1", commodity_move="up", sector="Energy", impact=0.6, date="2026-07-01"),
              _event("e2", commodity_move="up", sector="Energy", impact=0.5, date="2026-07-01"),
              _event("e3", sentiment=0.0, date="2026-07-01")]:
        e["enriched_at"] = e["datetime"] + "T00:00:00+00:00"
        _run(db.market_events.insert_one(e))
    stats = _run(mem.index_events(db))
    assert stats["processed"] == 3 and stats["resolved"] >= 2

    query = _event("q", commodity_move="up", sector="Energy", impact=0.55)
    result = _run(mem.similar_situations(db, query, k=5))
    ids = {n["id"] for n in result["neighbors"]}
    assert "e1" in ids and "e2" in ids
    assert result["summary"]["avg_return"] == pytest.approx(10.0)
    assert result["summary"]["positive_share"] == 1.0
