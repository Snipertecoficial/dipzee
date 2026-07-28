"""Unit tests for the market event engine (L2).

Offline: the deterministic scoring is tested directly over a built graph, entity
extraction uses the keyword path (no LLM/network), and correlation runs against
the fake in-memory DB. LLM enrichment is exercised only via a monkeypatched
extractor so no provider/network is touched.
"""
import asyncio

import pytest

import event_service as ev
import knowledge_graph as kg
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


COMPANIES = [
    {"ticker": "XOM", "name": "Exxon", "sector": "Energy"},
    {"ticker": "JPM", "name": "JPMorgan", "sector": "Financial Services"},
    {"ticker": "O", "name": "Realty Income", "sector": "Real Estate"},
    {"ticker": "F", "name": "Ford", "sector": "Consumer Cyclical"},
    {"ticker": "AAPL", "name": "Apple", "sector": "Technology"},
]


@pytest.fixture
def graph():
    return kg.build_graph(COMPANIES)


@pytest.fixture(autouse=True)
def _reset_cache():
    kg._cache["graph"] = None
    kg._cache["at"] = 0.0
    yield


# --- keyword extraction ----------------------------------------------------- #

def test_keyword_extract_commodity_move():
    e = ev.keyword_extract({"headline": "Crude oil prices surge to a record high on strong demand"})
    ids = {c["id"]: c["move"] for c in e["commodities"]}
    assert ids.get("crude_oil") == "up"


def test_keyword_extract_macro_move():
    e = ev.keyword_extract({"headline": "Fed signals another rate hike to fight inflation"})
    macro = {m["id"]: m["move"] for m in e["macro"]}
    assert "interest_rates" in macro and "inflation" in macro


def test_keyword_extract_sentiment_and_ticker():
    e = ev.keyword_extract({"headline": "Company beats earnings, raises guidance", "ticker": "aapl"})
    assert e["companies"] == ["AAPL"]
    assert e["sentiment"] > 0


# --- deterministic scoring -------------------------------------------------- #

def test_score_direct_company(graph):
    extracted = {"companies": ["AAPL"], "sectors": [], "commodities": [], "macro": [],
                 "sentiment": 0.8, "materiality": 0.5, "method": "llm"}
    out = ev.score_event(extracted, graph)
    aapl = next(a for a in out["affected"] if a["symbol"] == "AAPL")
    assert aapl["impact"] == pytest.approx(0.4)  # 0.8 * 0.5
    assert aapl["confidence"] > 0


def test_score_commodity_up_splits_sign(graph):
    extracted = {"companies": [], "sectors": [], "commodities": [{"id": "crude_oil", "move": "up"}],
                 "macro": [], "sentiment": 0.0, "materiality": 1.0, "method": "llm"}
    by = {a["symbol"]: a for a in ev.score_event(extracted, graph)["affected"]}
    # Oil up: energy positive, consumer cyclical (autos) negative.
    assert by["XOM"]["impact"] > 0
    assert by["F"]["impact"] < 0


def test_score_rate_hike_bank_vs_reit(graph):
    extracted = {"companies": [], "sectors": [], "commodities": [],
                 "macro": [{"id": "interest_rates", "move": "up"}],
                 "sentiment": 0.0, "materiality": 1.0, "method": "llm"}
    by = {a["symbol"]: a for a in ev.score_event(extracted, graph)["affected"]}
    assert by["JPM"]["impact"] > 0   # banks benefit
    assert by["O"]["impact"] < 0     # REITs hurt


def test_score_unclear_move_ignored(graph):
    extracted = {"companies": [], "sectors": [], "commodities": [{"id": "crude_oil", "move": "unclear"}],
                 "macro": [], "sentiment": 0.0, "materiality": 1.0, "method": "keyword"}
    assert ev.score_event(extracted, graph)["affected"] == []


# --- sanitize + id ---------------------------------------------------------- #

def test_sanitize_drops_invalid_and_appends_ticker():
    raw = {"companies": ["msft"], "sectors": ["Energy", "Bogus"],
           "commodities": [{"id": "crude_oil", "move": "up"}, {"id": "unobtainium", "move": "up"}],
           "macro": [], "sentiment": 5, "event_type": "NONSENSE", "materiality": -3}
    s = ev._sanitize_extract(raw, {"ticker": "AAPL"})
    assert set(s["companies"]) == {"MSFT", "AAPL"}
    assert s["sectors"] == ["Energy"]
    assert [c["id"] for c in s["commodities"]] == ["crude_oil"]
    assert s["sentiment"] == 1.0 and s["materiality"] == 0.0   # clamped
    assert s["event_type"] == "other"


def test_event_id_stable_and_url_preferred():
    a = ev.event_id({"url": "http://x/1", "headline": "h"})
    b = ev.event_id({"url": "http://x/1", "headline": "different"})
    assert a == b and a.startswith("ev_")


# --- enrich + correlate (offline via keyword extractor) --------------------- #

@pytest.fixture
def fake_db():
    db = FakeDB()
    for c in COMPANIES:
        _run(db.assets.insert_one(dict(c)))
    return db


def _force_keyword(monkeypatch):
    async def fake_extract(item):
        return ev.keyword_extract(item)
    monkeypatch.setattr(ev, "extract_entities", fake_extract)


def test_enrich_event_shape(graph, monkeypatch):
    _force_keyword(monkeypatch)
    doc = _run(ev.enrich_event({"headline": "Crude oil surges", "url": "http://n/1"}, graph))
    assert doc["id"].startswith("ev_")
    assert doc["entities"]["commodities"][0]["id"] == "crude_oil"
    assert any(a["symbol"] == "XOM" for a in doc["affected"])


def test_correlate_dedups(fake_db, monkeypatch):
    _force_keyword(monkeypatch)
    items = [{"headline": "Crude oil surges", "url": "http://n/1"},
             {"headline": "Fed hikes rates", "url": "http://n/2"}]
    first = _run(ev.correlate(items, fake_db))
    assert first["new"] == 2
    # Re-running the same items processes nothing new.
    second = _run(ev.correlate(items, fake_db))
    assert second["new"] == 0 and second["skipped"] == 2
    stored = _run(fake_db.market_events.find({}).to_list(100))
    assert len(stored) == 2
