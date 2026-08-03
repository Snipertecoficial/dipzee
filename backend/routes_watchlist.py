"""Watchlist routes with per-plan limit enforcement."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from asset_service import refresh_asset
from database import db
from explain import build_explanation
from plans import has_feature, limit_for
from operation_lock import user_operation_lock
from security import require_feature

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistIn(BaseModel):
    ticker: str


@router.get("")
async def list_watchlist(user: dict = Depends(require_feature("watchlist"))):
    items = await db.watchlist_items.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    tickers = [it["ticker"] for it in items]
    assets = await db.assets.find({"ticker": {"$in": tickers}}, {"_id": 0}).to_list(500)
    by_ticker = {a["ticker"]: a for a in assets}
    loc = user.get("locale", "en")
    out = []
    for it in items:
        asset = by_ticker.get(it["ticker"])
        if asset and asset.get("score") is not None:
            asset = dict(asset)
            asset["explanation"] = build_explanation(asset, loc)
        out.append({"ticker": it["ticker"], "created_at": it["created_at"], "asset": asset})
    # sort by score desc (None last)
    out.sort(key=lambda x: (x["asset"]["score"] if x["asset"] and x["asset"].get("score") is not None else -1), reverse=True)
    return out


@router.post("")
async def add_watchlist(body: WatchlistIn, user: dict = Depends(require_feature("watchlist"))):
    from asset_service import normalize_ticker
    try:
        ticker = normalize_ticker(body.ticker)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker")
    asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    async with user_operation_lock(db, "watchlist-add", user["id"]):
        fresh_user = await db.users.find_one({"id": user["id"]})
        if not fresh_user or not has_feature(fresh_user.get("plan"), "watchlist"):
            raise HTTPException(status_code=403, detail="Watchlist access is no longer active")
        existing = await db.watchlist_items.find_one({"user_id": user["id"], "ticker": ticker})
        if existing:
            raise HTTPException(status_code=409, detail="Already in watchlist")
        limit = limit_for(fresh_user.get("plan", "none"), "watchlist")
        if limit is not None:
            count = await db.watchlist_items.count_documents({"user_id": user["id"]})
            if count >= limit:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "watchlist_limit", "limit": limit, "message": f"Your plan allows up to {limit} watchlist assets. Upgrade to add more."},
                )
        item = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "ticker": ticker,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.watchlist_items.insert_one(item)
    # Anonymized interest signal for the proprietary dataset (L5).
    from dataset_service import log_decision
    await log_decision(db, "watchlist_add", ticker, user=user)
    return {"ticker": ticker, "created_at": item["created_at"], "asset": asset}


@router.delete("/{ticker}")
async def remove_watchlist(ticker: str, user: dict = Depends(require_feature("watchlist"))):
    from asset_service import normalize_ticker
    try:
        ticker = normalize_ticker(ticker)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker")
    res = await db.watchlist_items.delete_one({"user_id": user["id"], "ticker": ticker})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    return {"ok": True}
