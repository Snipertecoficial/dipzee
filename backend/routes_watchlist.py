"""Watchlist routes with per-plan limit enforcement."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from asset_service import refresh_asset
from database import db
from explain import build_explanation
from plans import limit_for
from security import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistIn(BaseModel):
    ticker: str


@router.get("")
async def list_watchlist(user: dict = Depends(get_current_user)):
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
async def add_watchlist(body: WatchlistIn, user: dict = Depends(get_current_user)):
    ticker = body.ticker.strip().upper()
    existing = await db.watchlist_items.find_one({"user_id": user["id"], "ticker": ticker})
    if existing:
        raise HTTPException(status_code=400, detail="Already in watchlist")

    limit = limit_for(user.get("plan", "free"), "watchlist")
    if limit is not None:
        count = await db.watchlist_items.count_documents({"user_id": user["id"]})
        if count >= limit:
            raise HTTPException(
                status_code=403,
                detail={"code": "watchlist_limit", "limit": limit, "message": f"Free plan allows up to {limit} watchlist assets. Upgrade to add more."},
            )

    asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

    item = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "ticker": ticker,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.watchlist_items.insert_one(item)
    return {"ticker": ticker, "created_at": item["created_at"], "asset": asset}


@router.delete("/{ticker}")
async def remove_watchlist(ticker: str, user: dict = Depends(get_current_user)):
    ticker = ticker.strip().upper()
    res = await db.watchlist_items.delete_one({"user_id": user["id"], "ticker": ticker})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    return {"ok": True}
