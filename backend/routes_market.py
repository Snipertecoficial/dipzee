"""Resilient market-data REST endpoints (mounted under /api/market).

Design goals:
- Clean REST surface for the SaaS frontend/clients.
- Never surface transient upstream failures: responses are served from cache and
  fall back to the last-known-good snapshot (flagged `stale=true`) when Yahoo is
  rate-limited or unreachable. A hard 502 only happens when no data ever existed.
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import market_service as ms
from market_cache import cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

# TTL (seconds) per data type — aggressive caching protects the upstream.
TTL_QUOTE = 15
TTL_HISTORY = 3600
TTL_BATCH = 900
TTL_SUMMARY = 300
TTL_SEARCH = 300
TTL_FUNDAMENTALS = 86400
TTL_OPTIONS = 3600
TTL_SCREENER = 300


class MarketEnvelope(BaseModel):
    ok: bool = True
    data: Any = None
    cached: bool = False
    stale: bool = False
    fetched_at: Optional[str] = None


def _respond(envelope: Optional[dict], not_found_msg: str = "no_data"):
    if envelope is None:
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_unavailable", "message": not_found_msg},
        )
    return MarketEnvelope(ok=True, **envelope)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "market", "provider": "finnhub+yfinance"}


@router.get("/quote/{symbol}", response_model=MarketEnvelope)
async def get_quote(symbol: str):
    env = await cached(f"quote:{symbol.upper()}", TTL_QUOTE, lambda: ms.quote(symbol))
    return _respond(env, f"quote unavailable for {symbol}")


@router.get("/history/{symbol}", response_model=MarketEnvelope)
async def get_history(
    symbol: str,
    period: str = Query("1mo"),
    interval: str = Query("1d"),
):
    key = f"history:{symbol.upper()}:{period}:{interval}"
    env = await cached(key, TTL_HISTORY, lambda: ms.history(symbol, period, interval))
    return _respond(env, f"history unavailable for {symbol}")


@router.get("/batch", response_model=MarketEnvelope)
async def get_batch(
    symbols: str = Query(..., description="Comma-separated tickers, e.g. AAPL,MSFT,GOOG"),
    period: str = Query("1mo"),
    interval: str = Query("1d"),
):
    syms = [s for s in (symbols or "").split(",") if s.strip()]
    if not syms:
        raise HTTPException(status_code=400, detail={"error": "bad_request", "message": "symbols is required"})
    key = f"batch:{','.join(sorted(s.upper() for s in syms))}:{period}:{interval}"
    env = await cached(key, TTL_BATCH, lambda: ms.batch(syms, period, interval))
    return _respond(env, "batch unavailable")


@router.get("/summary/{market}", response_model=MarketEnvelope)
async def get_summary(market: str):
    env = await cached(f"summary:{market.upper()}", TTL_SUMMARY, lambda: ms.market_summary(market))
    return _respond(env, f"summary unavailable for {market}")


@router.get("/search", response_model=MarketEnvelope)
async def get_search(q: str = Query(..., min_length=1)):
    env = await cached(f"search:{q.lower().strip()}", TTL_SEARCH, lambda: ms.search(q))
    return _respond(env, "search unavailable")


@router.get("/fundamentals/{symbol}", response_model=MarketEnvelope)
async def get_fundamentals(symbol: str):
    env = await cached(f"fundamentals:{symbol.upper()}", TTL_FUNDAMENTALS, lambda: ms.fundamentals(symbol))
    return _respond(env, f"fundamentals unavailable for {symbol}")


@router.get("/options/{symbol}", response_model=MarketEnvelope)
async def get_options(symbol: str, expiration: Optional[str] = Query(None)):
    key = f"options:{symbol.upper()}:{expiration or 'dates'}"
    env = await cached(key, TTL_OPTIONS, lambda: ms.options(symbol, expiration))
    return _respond(env, f"options unavailable for {symbol}")


@router.get("/screener", response_model=MarketEnvelope)
async def get_screener(
    type: str = Query("day_gainers", description="Predefined screen key, e.g. day_gainers"),
    count: int = Query(25, ge=1, le=100),
):
    key = f"screener:{type}:{count}"
    env = await cached(key, TTL_SCREENER, lambda: ms.screener(type, count))
    return _respond(env, f"screener unavailable for {type}")
