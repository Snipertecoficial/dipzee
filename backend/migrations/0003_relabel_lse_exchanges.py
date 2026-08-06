"""Relabel LSE-vendor catalog rows with their real listing exchange and backfill
catalog scores.

The London Strategic Edge catalog carries no exchange field, so the initial
import stamped every instrument as exchange "LSE" — the DATA VENDOR, not the
listing venue — making Hong Kong (`0001.HK`) and Korea (`000270.KS`) tickers show
as "LSE" in Markets/Explore. This recomputes the real venue from the ticker
suffix for existing rows, and copies the Opportunity Score onto the catalog so
Explore leads with scored, recognizable names. DB-only, cheap, idempotent —
new imports already produce the correct values.
"""
from pymongo import UpdateOne


async def up(db):
    import security_master as sm

    ops = []
    async for r in db.security_master.find(
        {"source": "lse"},
        {"_id": 1, "symbol": 1, "country": 1, "asset_class": 1},
    ):
        venue = sm._lse_exchange(r.get("symbol", "") or "", r.get("country"), r.get("asset_class") or "")
        ops.append(UpdateOne({"_id": r["_id"]}, {"$set": {"exchange": venue, "exchange_code": venue}}))
    for i in range(0, len(ops), 1000):
        await db.security_master.bulk_write(ops[i:i + 1000], ordered=False)

    # Backfill Opportunity Score + classification (and verified dividends) onto
    # the browsable catalog so Explore can surface a score immediately.
    await sm.enrich_dividends_from_assets()
