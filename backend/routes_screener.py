"""Screener routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from explain import build_explanation
from screener_service import query_screener, refresh_universe, list_sectors, list_exchanges, RefreshCooldownError
from security import require_feature

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("")
async def get_screener(
    sector: Optional[str] = Query(None, max_length=80),
    exchange: Optional[str] = Query(None, max_length=20),
    classification: Optional[str] = Query(None, pattern=r"^(strong_buy|buy|hold|reduce|sell)$"),
    min_dividend: Optional[float] = Query(None, ge=0, le=1),
    max_range_position: Optional[float] = Query(None, ge=0, le=1),
    min_upside: Optional[float] = Query(None, ge=-10, le=10),
    user: dict = Depends(require_feature("screener")),
):
    filters = {
        "sector": sector,
        "exchange": exchange,
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
async def sectors(user: dict = Depends(require_feature("screener"))):
    return {"sectors": await list_sectors()}


@router.get("/exchanges")
async def exchanges(user: dict = Depends(require_feature("screener"))):
    return {"exchanges": await list_exchanges()}


@router.post("/refresh")
async def refresh(limit: Optional[int] = Query(None, ge=1, le=500), user: dict = Depends(require_feature("screener"))):
    try:
        count = await refresh_universe(limit=limit)
    except RefreshCooldownError as e:
        raise HTTPException(
            status_code=429,
            detail={"message": f"Screener was just refreshed. Try again in {e.retry_after_seconds}s.", "retry_after": e.retry_after_seconds},
        )
    return {"refreshed": count}
