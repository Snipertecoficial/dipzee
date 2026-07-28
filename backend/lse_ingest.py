"""LSE ingestion: pull normalized data for the tracked universe into Mongo.

Kept separate from ``lse_service.py`` (a pure SDK wrapper) so the DB-writing
concern is isolated. The scheduler's ``lse_ingest_job`` calls ``run_ingestion``.

Design:
- Only the *tracked universe* is ingested (watchlists + active alerts), never
  the full 22k-instrument catalog — that keeps storage and budget bounded.
- Every fetch is budget-guarded inside ``lse_service``. If the budget is
  exhausted mid-run, ``LSEBudgetError`` stops the whole run cleanly (we don't
  keep hammering) and the run is recorded as budget-stopped.
- Upserts are keyed for point-in-time correctness: candles by
  (symbol, timeframe, ts), dividends by (symbol, ex_date), splits by
  (symbol, date). Re-ingesting the same period updates in place, never dupes.
"""
import logging
from datetime import datetime, timezone

import lse_service as lse
from database import db

logger = logging.getLogger(__name__)

# Daily candles retained per symbol per run (kept modest for budget/storage).
CANDLE_TIMEFRAME = "1d"
CANDLE_LIMIT = 120


async def _upsert_many(collection, key_fields: list, docs: list) -> int:
    """Upsert normalized docs keyed by `key_fields`, stamping ingested_at.
    Returns the number processed. Isolated per-doc so one bad row can't abort
    the batch."""
    count = 0
    now = datetime.now(timezone.utc).isoformat()
    for d in docs:
        if not d:
            continue
        key = {f: d.get(f) for f in key_fields}
        if any(v is None for v in key.values()):
            continue
        try:
            await collection.update_one(key, {"$set": {**d, "ingested_at": now}}, upsert=True)
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("[lse ingest] upsert failed for %s: %s", key, e)
    return count


async def ingest_symbol(symbol: str) -> dict:
    """Ingest candles/dividends/splits/fundamentals for one symbol. Each source
    is isolated; a LSEBudgetError propagates (so the caller can stop the run)."""
    symbol = (symbol or "").strip().upper()
    result = {"symbol": symbol, "candles": 0, "dividends": 0, "splits": 0, "fundamentals": 0}
    if not symbol:
        return result

    rows = await lse.candles(symbol, CANDLE_TIMEFRAME, limit=CANDLE_LIMIT)
    norm = [lse.normalize_candle(symbol, CANDLE_TIMEFRAME, r) for r in (rows or [])]
    result["candles"] = await _upsert_many(db.lse_candles, ["symbol", "timeframe", "ts"], norm)

    divs = await lse.dividends(symbol)
    norm = [lse.normalize_dividend(symbol, r) for r in (divs or [])]
    result["dividends"] = await _upsert_many(db.lse_dividends, ["symbol", "ex_date"], norm)

    sp = await lse.splits(symbol)
    norm = [lse.normalize_split(symbol, r) for r in (sp or [])]
    result["splits"] = await _upsert_many(db.lse_splits, ["symbol", "date"], norm)

    fundamentals = await lse.fundamentals(symbol)
    if fundamentals:
        now = datetime.now(timezone.utc).isoformat()
        await db.lse_fundamentals.update_one(
            {"symbol": symbol},
            {"$set": {"symbol": symbol, "data": fundamentals, "source": "lse", "ingested_at": now}},
            upsert=True,
        )
        result["fundamentals"] = 1

    return result


async def _tracked_universe() -> list:
    """Symbols to ingest: everything in a watchlist or an active alert."""
    symbols = set()
    async for item in db.watchlist_items.find({}, {"ticker": 1}):
        if item.get("ticker"):
            symbols.add(item["ticker"].strip().upper())
    async for alert in db.alerts.find({"active": True}, {"ticker": 1}):
        if alert.get("ticker"):
            symbols.add(alert["ticker"].strip().upper())
    return sorted(symbols)


async def run_ingestion(symbols: list = None, max_symbols: int = None) -> dict:
    """Ingest the tracked universe (or an explicit symbol list). Budget-aware:
    stops cleanly when the LSE budget is exhausted. Records a run in
    ``lse_ingest_log`` for admin visibility. Never raises."""
    started = datetime.now(timezone.utc)
    if symbols is None:
        symbols = await _tracked_universe()
    if max_symbols:
        symbols = symbols[:max_symbols]

    summary = {
        "at": started.isoformat(),
        "symbols_requested": len(symbols),
        "symbols_done": 0,
        "candles": 0, "dividends": 0, "splits": 0, "fundamentals": 0,
        "errors": 0,
        "budget_stopped": False,
        "configured": lse.is_configured(),
    }

    if not lse.is_configured():
        logger.info("[lse ingest] skipped: LSE not configured")
        summary["duration_s"] = 0.0
        await _record(summary)
        return summary

    for sym in symbols:
        try:
            r = await ingest_symbol(sym)
            summary["symbols_done"] += 1
            for k in ("candles", "dividends", "splits", "fundamentals"):
                summary[k] += r[k]
        except lse.LSEBudgetError as e:
            logger.warning("[lse ingest] budget reached, stopping run: %s", e)
            summary["budget_stopped"] = True
            break
        except lse.LSENotConfigured:
            summary["configured"] = False
            break
        except Exception as e:  # noqa: BLE001 - one symbol must not abort the run
            summary["errors"] += 1
            logger.warning("[lse ingest] failed for %s: %s", sym, e)

    summary["duration_s"] = round((datetime.now(timezone.utc) - started).total_seconds(), 2)
    await _record(summary)
    logger.info("[lse ingest] done: %d/%d symbols, %d candles, budget_stopped=%s",
                summary["symbols_done"], summary["symbols_requested"], summary["candles"], summary["budget_stopped"])
    return summary


async def _record(summary: dict) -> None:
    try:
        await db.lse_ingest_log.insert_one(dict(summary))
    except Exception as e:  # noqa: BLE001
        logger.warning("[lse ingest] could not record run: %s", e)


async def last_ingest() -> dict:
    """Most recent ingestion-run summary (admin view)."""
    docs = await db.lse_ingest_log.find({}, {"_id": 0}).sort("at", -1).to_list(1)
    return docs[0] if docs else {}
