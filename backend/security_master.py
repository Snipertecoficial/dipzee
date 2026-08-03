"""Security master: the browsable multi-exchange asset catalog.

This is a *reference directory* (symbol -> exchange + type + name), NOT a
market-data feed. It powers the Markets "Explore" surface: filter every listed
US security (and, once LSE is configured, London instruments) by exchange and
asset class, search by symbol/name, paginate. Live prices are fetched on demand
for the visible page only (see /market/quotes) — the directory itself costs no
provider quota, so it scales to the full ~6k-symbol universe.

Source of truth for US listings is the canonical, public Nasdaq Trader Symbol
Directory (pipe-delimited, no auth):
  - nasdaqlisted.txt  (Nasdaq)
  - otherlisted.txt   (NYSE, NYSE American, NYSE Arca, Cboe BZX, IEX)
Fetched to ``data/nasdaq/`` and re-imported on a slow cadence (listings change
rarely). A comma-CSV drop of the same files is accepted as an offline fallback.

London (LSE) instruments are ingested separately via ``import_lse_catalog`` over
the licensed ``lse_service.catalog()`` — see [[lse-intelligence-layer]].
"""
import csv
import asyncio
import logging
import re
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Optional

from pymongo import UpdateOne

from database import db

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data" / "nasdaq"
_NASDAQ_TRADER = "https://www.nasdaqtrader.com/dynamic/SymDir"

# otherlisted.txt "Exchange" code -> human name. (nasdaqlisted.txt is all Nasdaq.)
_EXCHANGE = {
    "N": "NYSE",
    "P": "NYSE Arca",
    "A": "NYSE American",
    "Z": "Cboe BZX",
    "V": "IEX",
}

# Investable asset classes shown by default (spans conservative -> aggressive:
# bonds, stocks, ETFs, ADRs, indices, commodities, forex, crypto). The noisier
# structured/derivative classes (preferred, warrant, unit, right, note, yield,
# credit, future, fx_deriv, rate, volatility) sit behind the "Advanced" filter.
DEFAULT_VISIBLE_CLASSES = {"stock", "etf", "adr", "bond", "index", "commodity", "forex", "crypto"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Classification (high-standard, name- and symbol-driven)
# --------------------------------------------------------------------------- #
def classify(symbol: str, name: str, etf_flag: bool) -> str:
    """Map a listing to an asset class.

    Symbol suffixes are authoritative on the CQS/ACT files ($=preferred,
    .W/.WS=warrant, .U=unit, .R=right); otherwise the security name drives it
    (works for Nasdaq symbols too, which lack the suffix conventions). ETF flag
    wins first — an ETF is an ETF regardless of its name.
    """
    s = (symbol or "").upper()
    nl = (name or "").lower()

    if etf_flag:
        return "etf"
    if "$" in s:
        return "preferred"
    if s.endswith((".W", ".WS")):
        return "warrant"
    if s.endswith(".U"):
        return "unit"
    if s.endswith(".R"):
        return "right"
    if "warrant" in nl:
        return "warrant"
    if re.search(r"\bunits?\b", nl):
        return "unit"
    if re.search(r"\brights?\b", nl):  # \b keeps "Bright"/"Wright" out
        return "right"
    if "depositary" in nl or "depository" in nl:
        return "adr"
    if re.search(r"\b(notes?|debentures?|subordinated)\b", nl):
        return "note"
    if re.search(r"\b(preferred|preference|pfd)\b", nl):
        return "preferred"
    return "stock"


def _record(symbol: str, name: str, exchange: str, exchange_code: str,
            etf_flag: bool, source: str) -> Optional[dict]:
    symbol = (symbol or "").strip()
    name = (name or "").strip()
    if not symbol or not name:
        return None
    cls = classify(symbol, name, etf_flag)
    return {
        "symbol": symbol,
        "name": name,
        "name_lower": name.lower(),
        "exchange": exchange,
        "exchange_code": exchange_code,
        "asset_class": cls,
        "etf": bool(etf_flag),
        "source": source,
        "default_visible": cls in DEFAULT_VISIBLE_CLASSES,
        "updated_at": _now_iso(),
    }


# --------------------------------------------------------------------------- #
# Parsing (canonical pipe files + comma-CSV fallback)
# --------------------------------------------------------------------------- #
def _iter_pipe(text: str):
    """Yield dict rows from a Nasdaq Trader pipe-delimited file (drops footer)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return
    header = lines[0].split("|")
    for ln in lines[1:]:
        if ln.startswith("File Creation Time"):
            continue
        cols = ln.split("|")
        if len(cols) != len(header):
            continue
        yield dict(zip(header, cols))


def parse_nasdaq_listed(text: str) -> list:
    """nasdaqlisted.txt: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares"""
    out = []
    for r in _iter_pipe(text):
        if (r.get("Test Issue") or "").strip().upper() == "Y":
            continue
        rec = _record(r.get("Symbol"), r.get("Security Name"), "Nasdaq", "Q",
                      (r.get("ETF") or "").strip().upper() == "Y", "us")
        if rec:
            out.append(rec)
    return out


def parse_other_listed(text: str) -> list:
    """otherlisted.txt: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol"""
    out = []
    for r in _iter_pipe(text):
        if (r.get("Test Issue") or "").strip().upper() == "Y":
            continue
        code = (r.get("Exchange") or "").strip()
        rec = _record(r.get("ACT Symbol"), r.get("Security Name"),
                      _EXCHANGE.get(code, code or "US"), code,
                      (r.get("ETF") or "").strip().upper() == "Y", "us")
        if rec:
            out.append(rec)
    return out


def _parse_csv_fallback(path: Path) -> list:
    """Offline fallback: read a comma-CSV drop of the directory files.

    Handles both the metadata-rich other-listed format (has an 'Exchange'
    column + ETF flag) and the bare nyse-listed 2-column (Symbol, Name).
    """
    out = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = {c.strip(): c for c in (reader.fieldnames or [])}
        sym_col = cols.get("ACT Symbol") or cols.get("Symbol")
        name_col = cols.get("Security Name") or cols.get("Company Name")
        exch_col = cols.get("Exchange")
        etf_col = cols.get("ETF")
        test_col = cols.get("Test Issue")
        if not sym_col or not name_col:
            return out
        for r in reader:
            if test_col and (r.get(test_col) or "").strip().upper() == "Y":
                continue
            code = (r.get(exch_col) or "").strip() if exch_col else ""
            exchange = _EXCHANGE.get(code, code) if code else "NYSE"
            etf_flag = etf_col and (r.get(etf_col) or "").strip().upper() == "Y"
            rec = _record(r.get(sym_col), r.get(name_col), exchange, code, bool(etf_flag), "us")
            if rec:
                out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# Fetch + import
# --------------------------------------------------------------------------- #
def fetch_listings() -> dict:
    """Download the canonical Nasdaq Trader files into DATA_DIR. Best-effort:
    raises on network error so the caller can fall back to cached/CSV files."""
    import requests  # lazy: only when a fetch actually happens

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for fname in ("nasdaqlisted.txt", "otherlisted.txt"):
        resp = requests.get(f"{_NASDAQ_TRADER}/{fname}", timeout=30)
        resp.raise_for_status()
        (DATA_DIR / fname).write_text(resp.text, encoding="utf-8")
        out[fname] = len(resp.text)
    return out


async def _upsert(records: list) -> int:
    """Idempotent bulk upsert keyed by (symbol, source)."""
    if not records:
        return 0
    ops = [
        UpdateOne({"symbol": r["symbol"], "source": r["source"]}, {"$set": r}, upsert=True)
        for r in records
    ]
    # Chunk to keep individual bulk_write payloads bounded.
    written = 0
    for i in range(0, len(ops), 1000):
        res = await db.security_master.bulk_write(ops[i:i + 1000], ordered=False)
        written += (res.upserted_count or 0) + (res.modified_count or 0)
    return written


async def import_us_listings(fetch: bool = True) -> dict:
    """Import the US listed universe into security_master.

    Tries a fresh fetch first; on failure (or fetch=False) uses whatever is
    cached in DATA_DIR (the .txt files, or a comma-CSV drop). Returns a summary.
    """
    fetched = None
    if fetch:
        try:
            fetched = await asyncio.to_thread(fetch_listings)
        except Exception as e:  # noqa: BLE001 - network/HTTP; fall back to cache
            logger.warning("[catalog] fetch_listings failed, using cached files: %s", e)

    records: list = []
    nasdaq_txt = DATA_DIR / "nasdaqlisted.txt"
    other_txt = DATA_DIR / "otherlisted.txt"
    if nasdaq_txt.exists():
        records += parse_nasdaq_listed(nasdaq_txt.read_text(encoding="utf-8"))
    if other_txt.exists():
        records += parse_other_listed(other_txt.read_text(encoding="utf-8"))
    if not records:  # offline CSV fallback (user-provided directory dumps)
        for csv_path in sorted(DATA_DIR.glob("*.csv")):
            records += _parse_csv_fallback(csv_path)

    # De-dupe by symbol (a symbol can appear once per file); last write wins.
    dedup = {r["symbol"]: r for r in records}
    written = await _upsert(list(dedup.values()))
    logger.info("[catalog] US import: %d parsed, %d unique, %d written", len(records), len(dedup), written)
    return {"fetched": fetched, "parsed": len(records), "unique": len(dedup), "written": written}


# --------------------------------------------------------------------------- #
# LSE (London) catalog ingestion
# --------------------------------------------------------------------------- #
# London Strategic Edge is a global multi-asset data vendor (not the London
# Stock Exchange). Its catalog category -> our asset_class. Economics (macro
# series -> the intelligence/macro layer) and Options (options-availability on
# underlyings, not distinct browsable assets) are intentionally excluded.
_LSE_SKIP_CATEGORIES = {"economics", "options"}
_LSE_CLASS = {
    "stocks": "stock", "stock": "stock", "equity": "stock", "equities": "stock",
    "etfs": "etf", "etf": "etf", "fund": "etf",
    "adr": "adr",
    "forex": "forex", "fx": "forex",
    "crypto": "crypto",
    "commodities": "commodity", "commodity": "commodity",
    "indices": "index", "index": "index", "currency index": "index",
    "bonds": "bond", "corporate_bonds": "bond", "bond_futures": "bond",
    "sovereign_yields": "yield",
    "credit_indices": "credit",
    "futures": "future",
    "fx_derivatives": "fx_deriv",
    "interest rates": "rate", "interest_rates": "rate",
    "volatility": "volatility",
}


async def import_lse_catalog() -> dict:
    """Ingest the licensed London Strategic Edge instrument catalog into
    security_master (source='lse'). Covers every investable class (bonds ->
    crypto), skips macro/options series, and de-dupes stocks already in the US
    directory. No-op when LSE isn't configured."""
    import lse_service

    if not lse_service.is_configured():
        return {"configured": False, "written": 0}

    raw = await lse_service.catalog()  # budget-guarded in lse_service
    items = raw if isinstance(raw, list) else (raw or {}).get("data") or (raw or {}).get("instruments") or []

    # A stock already listed in the US directory is the same security — keep the
    # US row, drop the LSE duplicate (by symbol).
    us_syms = set(await db.security_master.distinct("symbol", {"source": "us"}))

    records = []
    skipped_cat = skipped_dupe = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        category = (it.get("category") or it.get("dataset") or it.get("type") or "").strip().lower()
        if category in _LSE_SKIP_CATEGORIES:
            skipped_cat += 1
            continue
        cls = _LSE_CLASS.get(category)
        if cls is None:
            skipped_cat += 1
            continue
        symbol = (it.get("symbol") or it.get("ticker") or it.get("code") or "").strip()
        name = (it.get("name") or it.get("description") or symbol).strip()
        if not symbol or not name:
            continue
        if cls == "stock" and symbol in us_syms:
            skipped_dupe += 1
            continue
        records.append({
            "symbol": symbol,
            "name": name,
            "name_lower": name.lower(),
            "exchange": "LSE",
            "exchange_code": "LSE",
            "asset_class": cls,
            "etf": cls == "etf",
            "source": "lse",
            "country": it.get("country"),
            "default_visible": cls in DEFAULT_VISIBLE_CLASSES,
            "updated_at": _now_iso(),
        })
    dedup = {r["symbol"]: r for r in records}
    written = await _upsert(list(dedup.values()))
    logger.info("[catalog] LSE import: %d kept, %d skipped(cat), %d skipped(dupe), %d written",
                len(dedup), skipped_cat, skipped_dupe, written)
    return {
        "configured": True,
        "instruments": len(dedup),
        "skipped_categories": skipped_cat,
        "skipped_dupes": skipped_dupe,
        "written": written,
    }


# --------------------------------------------------------------------------- #
# Query (browse / search / facets)
# --------------------------------------------------------------------------- #
def _build_query(q, exchange, asset_class, source, advanced, min_dividend=None) -> dict:
    query: dict = {}
    if source:
        query["source"] = source
    if exchange:
        query["exchange"] = exchange
    if asset_class:
        query["asset_class"] = asset_class
    elif not advanced:
        query["default_visible"] = True
    if min_dividend is not None:
        # $gte on a missing field never matches, so this correctly returns only
        # rows we have verified dividend data for (never fabricated).
        query["dividend_yield"] = {"$gte": float(min_dividend)}
    if q and q.strip():
        term = q.strip()
        query["$or"] = [
            {"symbol": {"$regex": "^" + re.escape(term.upper())}},
            {"name_lower": {"$regex": re.escape(term.lower())}},
        ]
    return query


async def search_catalog(q: Optional[str] = None, exchange: Optional[str] = None,
                         asset_class: Optional[str] = None, source: Optional[str] = None,
                         advanced: bool = False, min_dividend: Optional[float] = None,
                         page: int = 1, page_size: int = 25) -> dict:
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 25)))
    query = _build_query(q, exchange, asset_class, source, advanced, min_dividend)
    total = await db.security_master.count_documents(query)
    rows = await (
        db.security_master.find(query, {"_id": 0, "name_lower": 0})
        .sort("symbol", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(page_size)
    )
    return {
        "results": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }


async def facets(source: Optional[str] = None, advanced: bool = False) -> dict:
    """Exchange + asset-class chips with counts, honoring the default-visible
    filter unless advanced=True. Uses distinct+count (FakeDB-friendly, N small)."""
    base: dict = {}
    if source:
        base["source"] = source
    if not advanced:
        base["default_visible"] = True

    exchanges = []
    for name in await db.security_master.distinct("exchange", base):
        if not name:
            continue
        n = await db.security_master.count_documents({**base, "exchange": name})
        exchanges.append({"name": name, "count": n})
    exchanges.sort(key=lambda x: x["count"], reverse=True)

    classes = []
    # Class facets ignore the default-visible gate so the "Advanced" chip can
    # advertise what's hidden; still respects the source filter.
    cbase = {"source": source} if source else {}
    for cls in await db.security_master.distinct("asset_class", cbase):
        if not cls:
            continue
        n = await db.security_master.count_documents({**cbase, "asset_class": cls})
        classes.append({"name": cls, "count": n})
    classes.sort(key=lambda x: x["count"], reverse=True)

    return {
        "exchanges": exchanges,
        "asset_classes": classes,
        "total": await db.security_master.count_documents(base),
    }


async def enrich_dividends_from_assets() -> dict:
    """Copy verified dividend yields from the scored ``assets`` collection into
    security_master (matched by symbol) so the "pays dividends" filter and the
    per-row yield badge use REAL data. Coverage grows as more names get
    refreshed; rows without data simply stay unmarked — never fabricated."""
    ops = []
    async for a in db.assets.find({"dividend_yield": {"$ne": None}}, {"_id": 0, "ticker": 1, "dividend_yield": 1}):
        sym = (a.get("ticker") or "").strip()
        dy = a.get("dividend_yield")
        if not sym or dy is None:
            continue
        ops.append(UpdateOne(
            {"symbol": sym},
            {"$set": {"dividend_yield": float(dy), "pays_dividend": float(dy) > 0}},
        ))
    written = 0
    for i in range(0, len(ops), 1000):
        res = await db.security_master.bulk_write(ops[i:i + 1000], ordered=False)
        written += (res.modified_count or 0)
    logger.info("[catalog] dividend enrich: %d assets -> %d rows updated", len(ops), written)
    return {"assets": len(ops), "updated": written}


async def catalog_status() -> dict:
    """Admin summary: totals by source, last update."""
    total = await db.security_master.count_documents({})
    us = await db.security_master.count_documents({"source": "us"})
    lse = await db.security_master.count_documents({"source": "lse"})
    latest = await db.security_master.find({}, {"_id": 0, "updated_at": 1}).sort("updated_at", -1).limit(1).to_list(1)
    return {
        "total": total,
        "by_source": {"us": us, "lse": lse},
        "last_updated": latest[0].get("updated_at") if latest else None,
    }
