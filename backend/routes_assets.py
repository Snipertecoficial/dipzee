"""Asset routes: score, refresh, get, search."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from asset_service import refresh_asset
from database import db
from explain import build_explanation
from market_cache import cached
from providers import get_company_news, get_market_news, get_fmp_news, get_yf_news, search_resilient
from security import get_current_user
from alert_service import evaluate_alerts_for_asset

router = APIRouter(tags=["assets"])

TTL_NEWS = 180  # 3min — short enough to feel live, long enough to not hammer Yahoo.


def _with_explanation(asset: dict, locale: str) -> dict:
    if asset and asset.get("score") is not None:
        asset = dict(asset)
        asset["explanation"] = build_explanation(asset, locale)
    return asset


@router.get("/assets/search")
async def search_assets(q: str = Query(..., min_length=1), user: dict = Depends(get_current_user)):
    return {"results": await asyncio.to_thread(search_resilient, q)}


@router.get("/assets/{ticker}/news")
async def asset_news(ticker: str, user: dict = Depends(get_current_user)):
    ticker = ticker.strip().upper()
    news = get_company_news(ticker, days=7, limit=15)  # Finnhub, needs FINNHUB_API_KEY
    if not news:
        # Free fallback: no key needed, so this always has a chance of working.
        env = await cached(f"yfnews:{ticker}", TTL_NEWS, lambda: get_yf_news(ticker, limit=15))
        news = (env or {}).get("data") or []
    return {"news": news}


@router.get("/news/market")
async def market_news(user: dict = Depends(get_current_user)):
    news = get_market_news(limit=20)       # Finnhub, needs FINNHUB_API_KEY
    news += get_fmp_news(limit=15)         # FMP, needs a plan that isn't restricted to /stable basics
    if not news:
        env = await cached("yfnews:market", TTL_NEWS, lambda: get_yf_news(limit=20))
        news = (env or {}).get("data") or []
    return {"news": news}


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


# USER-FACING OPERATIONS FOR ANNOUNCEMENTS & SPONSOR ADS
from datetime import datetime, timezone

@router.get("/announcements/active")
async def get_active_announcements(user: dict = Depends(get_current_user)):
    now_str = datetime.now(timezone.utc).isoformat()
    query = {
        "active": True,
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gt": now_str}}
        ]
    }
    announcements = await db.announcements.find(query).to_list(100)
    for a in announcements:
        a.pop("_id", None)
    return {"announcements": announcements}

@router.get("/partner-ads/active")
async def get_active_partner_ads(user: dict = Depends(get_current_user)):
    ads = await db.partner_ads.find({"active": True}).to_list(100)
    for a in ads:
        a.pop("_id", None)
    return {"ads": ads}

@router.post("/partner-ads/click/{ad_id}")
async def register_ad_click(ad_id: str, user: dict = Depends(get_current_user)):
    ad = await db.partner_ads.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    await db.partner_ads.update_one({"id": ad_id}, {"$inc": {"clicks": 1}})
    return {"target_url": ad.get("target_url")}

