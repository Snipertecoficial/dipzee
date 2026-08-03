"""Portfolio / positions with computed P&L (Investor feature)."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from asset_service import refresh_asset
from database import db
from operation_lock import user_operation_lock
from plans import has_feature
from security import require_feature

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PositionIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=15)
    quantity: float = Field(gt=0, le=1_000_000_000, allow_inf_nan=False)
    avg_cost: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)


class PositionUpdate(BaseModel):
    quantity: Optional[float] = Field(default=None, gt=0, le=1_000_000_000, allow_inf_nan=False)
    avg_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000, allow_inf_nan=False)


async def _compute(user_id: str) -> dict:
    positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    items = []
    # Positions can span multiple currencies (e.g. a US stock in USD alongside a
    # TSX stock in CAD) — summing raw numbers across currencies into one total
    # would silently produce a meaningless blended figure, so totals are kept
    # per-currency instead.
    totals_by_currency: dict = {}
    semaphore = asyncio.Semaphore(5)

    async def enrich(p):
        async with semaphore:
            asset = await refresh_asset(p["ticker"]) or {}
        return p, asset

    enriched = await asyncio.gather(*(enrich(position) for position in positions))
    for p, asset in enriched:
        price = asset.get("price")
        currency = asset.get("currency") or "USD"
        dy = asset.get("dividend_yield") or 0.0
        qty = p["quantity"]
        cost_basis = qty * p["avg_cost"]
        market_value = (qty * price) if price is not None else None
        pnl = (market_value - cost_basis) if market_value is not None else None
        pnl_pct = (pnl / cost_basis) if (pnl is not None and cost_basis) else None
        annual_income = (market_value * dy) if market_value is not None else None
        items.append({
            **p,
            "name": asset.get("name"),
            "price": price,
            "currency": currency,
            "dividend_yield": dy,
            "score": asset.get("score"),
            "classification": asset.get("classification"),
            "cost_basis": round(cost_basis, 2),
            "market_value": round(market_value, 2) if market_value is not None else None,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_pct": pnl_pct,
            "annual_income": round(annual_income, 2) if annual_income is not None else None,
        })
        if market_value is not None:
            bucket = totals_by_currency.setdefault(currency, {
                "currency": currency, "market_value": 0.0, "cost_basis": 0.0, "pnl": 0.0, "annual_income": 0.0,
            })
            bucket["market_value"] += market_value
            bucket["cost_basis"] += cost_basis
            bucket["pnl"] += pnl
            bucket["annual_income"] += annual_income or 0.0

    totals = []
    for bucket in totals_by_currency.values():
        bucket = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in bucket.items()}
        bucket["pnl_pct"] = (bucket["pnl"] / bucket["cost_basis"]) if bucket["cost_basis"] else None
        totals.append(bucket)
    totals.sort(key=lambda t: t["market_value"], reverse=True)

    items.sort(key=lambda x: (x.get("market_value") or 0), reverse=True)
    return {"positions": items, "totals": totals}


@router.get("")
async def get_portfolio(user: dict = Depends(require_feature("portfolio"))):
    return await _compute(user["id"])


@router.post("")
async def add_position(body: PositionIn, user: dict = Depends(require_feature("portfolio"))):
    from asset_service import normalize_ticker
    try:
        ticker = normalize_ticker(body.ticker)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker")
    if not await refresh_asset(ticker):
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    async with user_operation_lock(db, "position-add", user["id"]):
        fresh_user = await db.users.find_one({"id": user["id"]})
        if not fresh_user or not has_feature(fresh_user.get("plan"), "portfolio"):
            raise HTTPException(status_code=403, detail="Portfolio access is no longer active")
        existing = await db.positions.find_one({"user_id": user["id"], "ticker": ticker})
        if existing:
            # Merge: weighted average cost.
            total_qty = existing["quantity"] + body.quantity
            avg = ((existing["quantity"] * existing["avg_cost"]) + (body.quantity * body.avg_cost)) / total_qty
            await db.positions.update_one(
                {"id": existing["id"], "user_id": user["id"]},
                {"$set": {"quantity": total_qty, "avg_cost": round(avg, 4)}},
            )
        else:
            if await db.positions.count_documents({"user_id": user["id"]}) >= 500:
                raise HTTPException(status_code=422, detail="Portfolio position limit reached")
            await db.positions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "ticker": ticker,
                "quantity": body.quantity,
                "avg_cost": body.avg_cost,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    return await _compute(user["id"])


@router.put("/{position_id}")
async def update_position(position_id: str, body: PositionUpdate, user: dict = Depends(require_feature("portfolio"))):
    pos = await db.positions.find_one({"id": position_id, "user_id": user["id"]})
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    updates = {}
    if body.quantity is not None:
        updates["quantity"] = body.quantity
    if body.avg_cost is not None:
        updates["avg_cost"] = body.avg_cost
    if updates:
        await db.positions.update_one({"id": position_id, "user_id": user["id"]}, {"$set": updates})
    return await _compute(user["id"])


@router.delete("/{position_id}")
async def delete_position(position_id: str, user: dict = Depends(require_feature("portfolio"))):
    res = await db.positions.delete_one({"id": position_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Position not found")
    return await _compute(user["id"])
