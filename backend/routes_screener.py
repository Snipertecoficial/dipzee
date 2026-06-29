"""Screener routes."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from explain import build_explanation
from screener_service import query_screener, refresh_universe, list_sectors
from security import get_current_user

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("")
async def get_screener(
    sector: Optional[str] = None,
    classification: Optional[str] = None,
    min_dividend: Optional[float] = None,
    max_range_position: Optional[float] = None,
    min_upside: Optional[float] = None,
    user: dict = Depends(get_current_user),
):
    filters = {
        "sector": sector,
        "classification": classification,
        "min_dividend": min_dividend,
        "max_range_position": max_range_position,
        "min_upside": min_upside,
    }
    results = await query_screener(filters)
    loc = user.get("locale", "en")
    for a in results:
        try:
            a["explanation"] = build_explanation(a, loc)
        except Exception:
            a["explanation"] = None
    return {"results": results, "count": len(results)}


@router.get("/sectors")
async def sectors(user: dict = Depends(get_current_user)):
    return {"sectors": await list_sectors()}


@router.post("/refresh")
async def refresh(limit: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    count = await refresh_universe(limit=limit)
    return {"refreshed": count}
