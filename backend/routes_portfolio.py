"""Portfolio / positions with computed P&L (Investor feature)."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from asset_service import refresh_asset
from database import db
from security import require_feature

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PositionIn(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    avg_cost: float = Field(ge=0)


class PositionUpdate(BaseModel):
    quantity: Optional[float] = Field(default=None, gt=0)
    avg_cost: Optional[float] = Field(default=None, ge=0)


async def _compute(user_id: str) -> dict:
    positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    items = []
    totals = {"market_value": 0.0, "cost_basis": 0.0, "pnl": 0.0, "annual_income": 0.0, "currency": "USD"}
    for p in positions:
        asset = await refresh_asset(p["ticker"]) or {}
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
            totals["market_value"] += market_value
            totals["cost_basis"] += cost_basis
            totals["pnl"] += pnl
            totals["annual_income"] += annual_income or 0.0
            totals["currency"] = currency
    totals = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in totals.items()}
    totals["pnl_pct"] = (totals["pnl"] / totals["cost_basis"]) if totals["cost_basis"] else None
    items.sort(key=lambda x: (x.get("market_value") or 0), reverse=True)
    return {"positions": items, "totals": totals}


@router.get("")
async def get_portfolio(user: dict = Depends(require_feature("portfolio"))):
    return await _compute(user["id"])


@router.post("")
async def add_position(body: PositionIn, user: dict = Depends(require_feature("portfolio"))):
    ticker = body.ticker.strip().upper()
    await refresh_asset(ticker)
    existing = await db.positions.find_one({"user_id": user["id"], "ticker": ticker})
    if existing:
        # Merge: weighted average cost.
        total_qty = existing["quantity"] + body.quantity
        avg = ((existing["quantity"] * existing["avg_cost"]) + (body.quantity * body.avg_cost)) / total_qty
        await db.positions.update_one(
            {"id": existing["id"]},
            {"$set": {"quantity": total_qty, "avg_cost": round(avg, 4)}},
        )
    else:
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
        await db.positions.update_one({"id": position_id}, {"$set": updates})
    return await _compute(user["id"])


@router.delete("/{position_id}")
async def delete_position(position_id: str, user: dict = Depends(require_feature("portfolio"))):
    res = await db.positions.delete_one({"id": position_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Position not found")
    return await _compute(user["id"])
