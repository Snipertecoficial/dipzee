"""Unit tests for the security-master catalog (Explore surface).

Pure logic: asset-class classification, directory-file parsing, query building.
DB-backed (against the in-memory FakeDB): upsert idempotency, search/filter/
pagination, facets, offline US import, and mocked LSE ingestion.
"""
import asyncio

import pytest

import security_master as sm
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(sm, "db", db)
    return db


# --- classify --------------------------------------------------------------- #

@pytest.mark.parametrize("symbol,name,etf,expected", [
    ("AAPL", "Apple Inc. Common Stock", False, "stock"),
    ("QQQ", "Invesco QQQ Trust", True, "etf"),                       # ETF flag wins
    ("ABR$D", "Arbor Realty 6.375% Series D Preferred Stock", False, "preferred"),  # $ suffix
    ("XYZ", "Some Bank 5% Preferred Stock", False, "preferred"),     # name only
    ("ACHR.W", "Archer Aviation Warrants", False, "warrant"),        # .W suffix
    ("ABC", "SPAC Corp Warrant to purchase", False, "warrant"),      # name
    ("DEF.U", "SPAC Corp Units", False, "unit"),                     # .U suffix
    ("GHI", "SPAC Corp Units, each consisting of one share", False, "unit"),
    ("JKL.R", "SPAC Corp Rights", False, "right"),                   # .R suffix
    ("MNO", "SPAC Corp Rights to acquire one share", False, "right"),
    ("BABA", "Alibaba Group American Depositary Shares", False, "adr"),
    ("PQR", "Company 5.00% Senior Notes due 2030", False, "note"),
    ("STU", "Company 6% Subordinated Debentures", False, "note"),
])
def test_classify(symbol, name, etf, expected):
    assert sm.classify(symbol, name, etf) == expected


@pytest.mark.parametrize("symbol,name", [
    ("BRT", "Bright Industries Common Stock"),      # 'right' inside 'Bright' must NOT match
    ("WRT", "Wright Co Common Stock"),
    ("CMU", "Community Bankers Trust Common Stock"),  # 'unit' inside 'Community' must NOT match
])
def test_classify_word_boundaries(symbol, name):
    assert sm.classify(symbol, name, False) == "stock"


def test_default_visible_set():
    # Investable classes shown by default (conservative -> aggressive).
    assert sm.DEFAULT_VISIBLE_CLASSES == {"stock", "etf", "adr", "bond", "index", "commodity", "forex", "crypto"}


# --- parsing ---------------------------------------------------------------- #

NASDAQ_TXT = (
    "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
    "AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N\n"
    "QQQ|Invesco QQQ Trust|Q|N|N|100|Y|N\n"
    "ZTEST|Nasdaq Test Stock|G|Y|N|100|N|N\n"
    "File Creation Time: 0102202512:00|||||||\n"
)

OTHER_TXT = (
    "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
    "BRK.A|Berkshire Hathaway Inc. Common Stock|N|BRK.A|N|1|N|BRK.A\n"
    "ABR$D|Arbor Realty 6.375% Series D Preferred Stock|N|ABRpD|N|100|N|ABR-D\n"
    "ACHR.W|Archer Aviation Warrants|N|ACHR.WS|N|100|N|ACHR+\n"
    "SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY\n"
    "BABA|Alibaba Group American Depositary Shares|N|BABA|N|100|N|BABA\n"
    "ZTST|Test Issue Co|A|ZTST|N|100|Y|ZTST\n"
    "File Creation Time: 0102202512:00|||||||\n"
)


def test_parse_nasdaq_listed():
    recs = sm.parse_nasdaq_listed(NASDAQ_TXT)
    by = {r["symbol"]: r for r in recs}
    assert set(by) == {"AAPL", "QQQ"}            # ZTEST (test issue) + footer excluded
    assert by["AAPL"]["exchange"] == "Nasdaq" and by["AAPL"]["asset_class"] == "stock"
    assert by["QQQ"]["asset_class"] == "etf" and by["QQQ"]["etf"] is True
    assert by["AAPL"]["default_visible"] is True


def test_parse_other_listed_exchange_and_types():
    recs = sm.parse_other_listed(OTHER_TXT)
    by = {r["symbol"]: r for r in recs}
    assert "ZTST" not in by                       # test issue excluded
    assert by["BRK.A"]["exchange"] == "NYSE"
    assert by["SPY"]["exchange"] == "NYSE Arca" and by["SPY"]["asset_class"] == "etf"
    assert by["ABR$D"]["asset_class"] == "preferred" and by["ABR$D"]["default_visible"] is False
    assert by["ACHR.W"]["asset_class"] == "warrant" and by["ACHR.W"]["default_visible"] is False
    assert by["BABA"]["asset_class"] == "adr" and by["BABA"]["default_visible"] is True


def test_parse_csv_fallback(tmp_path):
    other = tmp_path / "other-listed.csv"
    other.write_text(
        "ACT Symbol,Company Name,Security Name,Exchange,CQS Symbol,ETF,Round Lot Size,Test Issue,NASDAQ Symbol\n"
        'A,"Agilent, Inc. Common Stock","Agilent, Inc. Common Stock",N,A,N,100.0,N,A\n'
        'SPYX,"SPDR Fund","SPDR Fund",P,SPYX,Y,100.0,N,SPYX\n'
        'ZZ,"Test","Test",A,ZZ,N,100.0,Y,ZZ\n',
        encoding="utf-8",
    )
    recs = sm._parse_csv_fallback(other)
    by = {r["symbol"]: r for r in recs}
    assert "ZZ" not in by
    assert by["A"]["exchange"] == "NYSE" and by["A"]["asset_class"] == "stock"
    # Comma inside the quoted company name is handled by the csv reader.
    assert by["A"]["name"].startswith("Agilent, Inc.")
    assert by["SPYX"]["exchange"] == "NYSE Arca" and by["SPYX"]["asset_class"] == "etf"


# --- query building --------------------------------------------------------- #

def test_build_query_default_visible_when_no_class():
    assert sm._build_query(None, None, None, None, False) == {"default_visible": True}


def test_build_query_class_overrides_default():
    assert sm._build_query(None, None, "etf", None, False) == {"asset_class": "etf"}


def test_build_query_advanced_drops_default():
    assert sm._build_query(None, None, None, None, True) == {}


def test_build_query_exchange_and_source():
    q = sm._build_query(None, "NYSE", None, "us", False)
    assert q == {"source": "us", "exchange": "NYSE", "default_visible": True}


def test_build_query_search_or():
    q = sm._build_query("app", None, None, None, False)
    assert q["default_visible"] is True
    assert q["$or"][0]["symbol"]["$regex"] == "^APP"
    assert q["$or"][1]["name_lower"]["$regex"] == "app"


# --- DB-backed: upsert / search / facets ------------------------------------ #

SEED = [
    {"symbol": "AAPL", "name": "Apple Inc", "name_lower": "apple inc", "exchange": "Nasdaq",
     "asset_class": "stock", "source": "us", "default_visible": True},
    {"symbol": "MSFT", "name": "Microsoft Corp", "name_lower": "microsoft corp", "exchange": "Nasdaq",
     "asset_class": "stock", "source": "us", "default_visible": True},
    {"symbol": "SPY", "name": "SPDR S&P 500", "name_lower": "spdr s&p 500", "exchange": "NYSE Arca",
     "asset_class": "etf", "source": "us", "default_visible": True},
    {"symbol": "ABR$D", "name": "Arbor Pref D", "name_lower": "arbor pref d", "exchange": "NYSE",
     "asset_class": "preferred", "source": "us", "default_visible": False},
    {"symbol": "HSBA", "name": "HSBC Holdings", "name_lower": "hsbc holdings", "exchange": "LSE",
     "asset_class": "stock", "source": "lse", "default_visible": True},
]


def _seed(db):
    _run(db.security_master.insert_many([dict(d) for d in SEED]))


def test_upsert_is_idempotent(fake_db):
    rec = sm._record("AAPL", "Apple Inc", "Nasdaq", "Q", False, "us")
    assert _run(sm._upsert([rec])) >= 0
    _run(sm._upsert([rec]))  # second write must not duplicate
    assert _run(fake_db.security_master.count_documents({"symbol": "AAPL", "source": "us"})) == 1


def test_search_default_hides_non_essential(fake_db):
    _seed(fake_db)
    res = _run(sm.search_catalog())
    classes = {r["asset_class"] for r in res["results"]}
    assert "preferred" not in classes           # hidden unless advanced/explicit
    assert res["total"] == 4                     # 5 seeded, 1 preferred hidden


def test_search_advanced_shows_all(fake_db):
    _seed(fake_db)
    res = _run(sm.search_catalog(advanced=True))
    assert res["total"] == 5


def test_search_filter_exchange_and_source(fake_db):
    _seed(fake_db)
    res = _run(sm.search_catalog(source="lse"))
    assert [r["symbol"] for r in res["results"]] == ["HSBA"]
    res2 = _run(sm.search_catalog(exchange="NYSE Arca"))
    assert [r["symbol"] for r in res2["results"]] == ["SPY"]


def test_search_query_symbol_and_name(fake_db):
    _seed(fake_db)
    assert [r["symbol"] for r in _run(sm.search_catalog(q="app"))["results"]] == ["AAPL"]
    # name contains match (case-insensitive), symbol prefix miss:
    assert [r["symbol"] for r in _run(sm.search_catalog(q="micro"))["results"]] == ["MSFT"]


def test_search_pagination(fake_db):
    _seed(fake_db)
    p1 = _run(sm.search_catalog(advanced=True, page=1, page_size=2))
    assert len(p1["results"]) == 2 and p1["pages"] == 3 and p1["total"] == 5
    p3 = _run(sm.search_catalog(advanced=True, page=3, page_size=2))
    assert len(p3["results"]) == 1


def test_facets(fake_db):
    _seed(fake_db)
    f = _run(sm.facets())
    ex = {e["name"]: e["count"] for e in f["exchanges"]}
    assert ex.get("Nasdaq") == 2 and ex.get("LSE") == 1
    # asset_class facets ignore default-visible so "preferred" is advertised.
    classes = {c["name"] for c in f["asset_classes"]}
    assert "preferred" in classes


def test_catalog_status(fake_db):
    _seed(fake_db)
    st = _run(sm.catalog_status())
    assert st["total"] == 5 and st["by_source"] == {"us": 4, "lse": 1}


# --- dividends: filter + enrichment from scored assets --------------------- #

def test_search_min_dividend_only_verified(fake_db):
    _run(fake_db.security_master.insert_many([
        {"symbol": "KO", "name": "Coca", "name_lower": "coca", "exchange": "NYSE",
         "asset_class": "stock", "source": "us", "default_visible": True, "dividend_yield": 0.031},
        {"symbol": "BRKB", "name": "Berkshire", "name_lower": "berkshire", "exchange": "NYSE",
         "asset_class": "stock", "source": "us", "default_visible": True, "dividend_yield": 0.0},
        {"symbol": "NVDA", "name": "Nvidia", "name_lower": "nvidia", "exchange": "Nasdaq",
         "asset_class": "stock", "source": "us", "default_visible": True},  # no verified yield
    ]))
    # >0 -> only real payers; unknown (no field) always excluded (never faked).
    assert [r["symbol"] for r in _run(sm.search_catalog(min_dividend=0.0001))["results"]] == ["KO"]
    # >=0 -> includes the verified zero-payer, still excludes the unknown.
    assert {r["symbol"] for r in _run(sm.search_catalog(min_dividend=0))["results"]} == {"BRKB", "KO"}


def test_enrich_dividends_from_assets(fake_db):
    _run(fake_db.security_master.insert_many([
        {"symbol": "KO", "name": "Coca", "name_lower": "coca", "exchange": "NYSE",
         "asset_class": "stock", "source": "us", "default_visible": True},
        {"symbol": "NVDA", "name": "Nvidia", "name_lower": "nvidia", "exchange": "Nasdaq",
         "asset_class": "stock", "source": "us", "default_visible": True},
    ]))
    _run(fake_db.assets.insert_many([
        {"ticker": "KO", "dividend_yield": 0.031},
        {"ticker": "NVDA", "dividend_yield": 0.0},
        {"ticker": "ZZZ", "dividend_yield": 0.05},  # not in catalog -> no-op
    ]))
    out = _run(sm.enrich_dividends_from_assets())
    assert out["assets"] == 3 and out["updated"] >= 1
    ko = _run(fake_db.security_master.find_one({"symbol": "KO"}))
    nv = _run(fake_db.security_master.find_one({"symbol": "NVDA"}))
    assert ko["dividend_yield"] == 0.031 and ko["pays_dividend"] is True
    assert nv["pays_dividend"] is False
    assert [r["symbol"] for r in _run(sm.search_catalog(min_dividend=0.0001))["results"]] == ["KO"]


# --- offline US import (parse -> upsert -> search) -------------------------- #

def test_import_us_offline(fake_db, tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "DATA_DIR", tmp_path)
    (tmp_path / "nasdaqlisted.txt").write_text(NASDAQ_TXT, encoding="utf-8")
    (tmp_path / "otherlisted.txt").write_text(OTHER_TXT, encoding="utf-8")
    summary = _run(sm.import_us_listings(fetch=False))
    assert summary["written"] >= 1
    # AAPL/SPY present; ZTEST/ZTST (test issues) absent.
    got = {r["symbol"] for r in _run(sm.search_catalog(advanced=True, page_size=100))["results"]}
    assert {"AAPL", "QQQ", "SPY", "BRK.A", "BABA"} <= got
    assert "ZTEST" not in got and "ZTST" not in got


# --- LSE ingestion (mocked catalog) ----------------------------------------- #

def test_import_lse_when_configured(fake_db, monkeypatch):
    import lse_service

    async def _fake_catalog(*a, **k):
        # Real LSE-vendor symbols carry a venue suffix; the exchange is derived
        # from it (London = .L, Hong Kong = .HK), never the vendor name "LSE".
        return [
            {"symbol": "HSBA.L", "name": "HSBC Holdings", "category": "stock", "country": "United Kingdom"},
            {"symbol": "VOD.L", "name": "Vodafone Group", "type": "equity", "country": "United Kingdom"},
            {"symbol": "ISF.L", "name": "iShares Core FTSE 100", "category": "etf", "country": "United Kingdom"},
            {"symbol": "0001.HK", "name": "CK Hutchison Holdings", "category": "stock", "country": "Hong Kong"},
        ]

    monkeypatch.setattr(lse_service, "is_configured", lambda: True)
    monkeypatch.setattr(lse_service, "catalog", _fake_catalog)
    out = _run(sm.import_lse_catalog())
    assert out["configured"] is True and out["instruments"] == 4
    res = _run(sm.search_catalog(source="lse", advanced=True))
    by = {r["symbol"]: r for r in res["results"]}
    assert by["HSBA.L"]["exchange"] == "LSE" and by["ISF.L"]["asset_class"] == "etf"
    assert by["VOD.L"]["asset_class"] == "stock"
    # Data vendor is LSE (source), but the listing venue is the real exchange.
    assert by["0001.HK"]["exchange"] == "HKEX" and by["0001.HK"]["source"] == "lse"


def test_import_lse_categories_skip_and_dedupe(fake_db, monkeypatch):
    import lse_service

    # AAPL already exists as a US listing -> the LSE stock dupe must be skipped.
    _run(fake_db.security_master.insert_one({
        "symbol": "AAPL", "name": "Apple Inc", "name_lower": "apple inc",
        "exchange": "Nasdaq", "asset_class": "stock", "source": "us", "default_visible": True,
    }))

    async def _fake_catalog(*a, **k):
        return [
            {"symbol": "BTC/USD", "name": "Bitcoin", "category": "Crypto"},
            {"symbol": "EUR/JPY", "name": "Euro / Yen", "category": "Forex"},
            {"symbol": "XAU/USD", "name": "Gold", "category": "Commodities"},
            {"symbol": "GDPUS", "name": "US GDP", "category": "Economics"},      # skipped
            {"symbol": "SPY", "name": "SPY options", "category": "Options"},     # skipped
            {"symbol": "AAPL", "name": "Apple", "category": "Stocks"},           # dupe -> skipped
            {"symbol": "RIO.L", "name": "Rio Tinto", "category": "Stocks", "country": "United Kingdom"},
        ]

    monkeypatch.setattr(lse_service, "is_configured", lambda: True)
    monkeypatch.setattr(lse_service, "catalog", _fake_catalog)
    out = _run(sm.import_lse_catalog())
    assert out["skipped_categories"] == 2       # economics + options
    assert out["skipped_dupes"] == 1            # AAPL already in US directory
    assert out["instruments"] == 4              # BTC/USD, EUR/JPY, XAU/USD, RIO.L

    res = _run(sm.search_catalog(source="lse", advanced=True))
    by = {r["symbol"]: r for r in res["results"]}
    assert set(by) == {"BTC/USD", "EUR/JPY", "XAU/USD", "RIO.L"}
    assert by["BTC/USD"]["asset_class"] == "crypto" and by["BTC/USD"]["default_visible"] is True
    assert by["EUR/JPY"]["asset_class"] == "forex"
    assert by["RIO.L"]["country"] == "United Kingdom" and by["RIO.L"]["asset_class"] == "stock"
    # Crypto/forex/commodity are default-visible (no "advanced" needed).
    assert _run(sm.search_catalog(source="lse"))["total"] == 4


def test_import_lse_noop_when_unconfigured(fake_db, monkeypatch):
    import lse_service
    monkeypatch.setattr(lse_service, "is_configured", lambda: False)
    out = _run(sm.import_lse_catalog())
    assert out == {"configured": False, "written": 0}
