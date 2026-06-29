"""Asset routes: score, refresh, get, search."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from asset_service import refresh_asset
from database import db
from explain import build_explanation
from providers import get_provider, get_company_news, get_market_news
from scoring import compute_opportunity_score, SETTINGS
from security import get_current_user
from alert_service import evaluate_alerts_for_asset

router = APIRouter(tags=["assets"])


def _with_explanation(asset: dict, locale: str) -> dict:
    if asset and asset.get("score") is not None:
        asset = dict(asset)
        asset["explanation"] = build_explanation(asset, locale)
    return asset


@router.get("/assets/search")
async def search_assets(q: str = Query(..., min_length=1), user: dict = Depends(get_current_user)):
    provider = get_provider()
    return {"results": provider.search(q)}


@router.get("/assets/{ticker}/news")
async def asset_news(ticker: str, user: dict = Depends(get_current_user)):
    return {"news": get_company_news(ticker, days=7, limit=15)}


@router.get("/news/market")
async def market_news(user: dict = Depends(get_current_user)):
    return {"news": get_market_news(limit=20)}


@router.get("/public/top-opportunities")
async def public_top_opportunities(limit: int = 8):
    """Public preview for the marketing/landing page (no auth)."""
    assets = await db.assets.find(
        {"score": {"$ne": None}}, {"_id": 0}
    ).sort("score", -1).to_list(limit)
    return {"results": assets}


@router.get("/score/{ticker}")
async def get_score(ticker: str, locale: Optional[str] = None, user: dict = Depends(get_current_user)):
    asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    loc = locale or user.get("locale", "en")
    asset = _with_explanation(asset, loc)
    return {
        "ticker": asset["ticker"],
        "score": asset.get("score"),
        "sub_scores": asset.get("sub_scores"),
        "classification": asset.get("classification"),
        "flags": asset.get("flags"),
        "explanation": asset.get("explanation"),
        "asset": asset,
    }


@router.post("/assets/refresh/{ticker}")
async def refresh(ticker: str, locale: Optional[str] = None, user: dict = Depends(get_current_user)):
    asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    # Evaluate any alerts that may now trigger on fresh data.
    await evaluate_alerts_for_asset(asset)
    loc = locale or user.get("locale", "en")
    return _with_explanation(asset, loc)


@router.get("/assets/{ticker}")
async def get_asset(ticker: str, locale: Optional[str] = None, user: dict = Depends(get_current_user)):
    ticker = ticker.strip().upper()
    asset = await db.assets.find_one({"ticker": ticker}, {"_id": 0})
    if not asset:
        asset = await refresh_asset(ticker)
    if not asset:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")
    loc = locale or user.get("locale", "en")
    return _with_explanation(asset, loc)
