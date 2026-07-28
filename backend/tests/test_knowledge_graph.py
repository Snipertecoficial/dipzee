"""Unit tests for the financial knowledge graph (L1).

All pure/offline: build a graph from curated seed + a small company list and
assert propagation reaches the right companies with sensible weights/signs. Plus
the DB-backed rebuild/load path against the fake in-memory DB.
"""
import asyncio

import pytest

import knowledge_graph as kg
import kg_seed
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


COMPANIES = [
    {"ticker": "XOM", "name": "Exxon", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "sector": "Energy"},
    {"ticker": "JPM", "name": "JPMorgan", "sector": "Financial Services"},
    {"ticker": "AAPL", "name": "Apple", "sector": "Technology"},
    {"ticker": "O", "name": "Realty Income", "sector": "Real Estate"},
    {"ticker": "RIO", "name": "Rio Tinto", "sector": "Materials"},  # alias -> Basic Materials
]


@pytest.fixture(autouse=True)
def _reset_cache():
    kg._cache["graph"] = None
    kg._cache["at"] = 0.0
    yield


# --- sector normalization --------------------------------------------------- #

def test_normalize_sector_aliases():
    assert kg_seed.normalize_sector("Materials") == "Basic Materials"
    assert kg_seed.normalize_sector("Financials") == "Financial Services"
    assert kg_seed.normalize_sector("Energy") == "Energy"
    assert kg_seed.normalize_sector("Nonsense") is None
    assert kg_seed.normalize_sector(None) is None


# --- graph build + membership ---------------------------------------------- #

def test_build_wires_company_to_sector():
    g = kg.build_graph(COMPANIES)
    assert kg.node_id("company", "XOM") in g.nodes
    # sector -> company membership edge exists
    energy = kg.node_id("sector", "Energy")
    dsts = [d for d, w, s in g.adj[energy]]
    assert kg.node_id("company", "XOM") in dsts and kg.node_id("company", "CVX") in dsts


def test_materials_alias_company_wired():
    g = kg.build_graph(COMPANIES)
    rio = g.nodes[kg.node_id("company", "RIO")]
    assert rio["sector"] == "Basic Materials"


# --- propagation ------------------------------------------------------------ #

def test_crude_oil_propagates_to_energy_companies_positive():
    g = kg.build_graph(COMPANIES)
    affected = g.affected_companies(kg.node_id("commodity", "crude_oil"))
    by_sym = {c["symbol"]: c for c in affected}
    # Energy names reached with positive sign (oil up helps energy).
    assert "XOM" in by_sym and by_sym["XOM"]["sign"] == 1
    assert by_sym["XOM"]["weight"] > 0
    # A consumer-cyclical/industrial drag would be negative — energy is positive.


def test_interest_rates_sign_split():
    g = kg.build_graph(COMPANIES)
    affected = {c["symbol"]: c for c in g.affected_companies(kg.node_id("macro", "interest_rates"))}
    # Rates up: banks benefit (+), REITs hurt (-).
    assert affected["JPM"]["sign"] == 1
    assert affected["O"]["sign"] == -1


def test_weight_decays_with_depth():
    g = kg.build_graph(COMPANIES)
    affected = {c["symbol"]: c for c in g.affected_companies(kg.node_id("commodity", "crude_oil"))}
    # commodity -> sector -> company is depth 2; weight < the raw exposure (0.9).
    assert affected["XOM"]["depth"] == 2
    assert affected["XOM"]["weight"] < 0.9


def test_min_weight_prunes_weak_paths():
    g = kg.build_graph(COMPANIES)
    # A very weak exposure (Utilities from crude_oil is -0.2) times decay^2 may
    # survive; raise min_weight so nothing does and the result is empty.
    affected = g.affected_companies(kg.node_id("commodity", "crude_oil"), min_weight=0.99)
    assert affected == []


# --- DB-backed rebuild/load ------------------------------------------------- #

@pytest.fixture
def fake_db():
    db = FakeDB()
    for c in COMPANIES:
        _run(db.assets.insert_one(dict(c)))
    return db


def test_rebuild_persists_nodes_and_edges(fake_db):
    counts = _run(kg.rebuild_graph(fake_db))
    assert counts["companies"] == len(COMPANIES)
    assert counts["nodes"] > len(COMPANIES)  # + sectors/commodities/macro
    assert counts["edges"] > 0
    stored_nodes = _run(fake_db.kg_nodes.find({}).to_list(1000))
    assert any(n["id"] == kg.node_id("company", "XOM") for n in stored_nodes)


def test_load_seeds_when_empty_then_propagates(fake_db):
    # Fresh DB (no kg_nodes yet) -> load_graph seeds it, then affected_assets works.
    companies = _run(kg.affected_assets(fake_db, kg.node_id("commodity", "crude_oil")))
    syms = {c["symbol"] for c in companies}
    assert "XOM" in syms and "CVX" in syms
