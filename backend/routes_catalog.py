"""Catalog routes — the Markets → Explore surface.

Browse/search the security-master directory (every US listed security, plus
London once LSE is configured) filtered by exchange and asset class. Metadata
only: prices are fetched on demand by the client for the visible page via
/market/quotes, so this endpoint costs no market-data provider quota.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

import security_master
from security import require_feature

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
async def browse_catalog(
    q: Optional[str] = Query(None, description="symbol prefix or name contains"),
    exchange: Optional[str] = None,
    asset_class: Optional[str] = None,
    source: Optional[str] = None,
    advanced: bool = False,
    min_dividend: Optional[float] = Query(None, description="only assets with a verified yield >= this (fraction, e.g. 0 for any payer)"),
    page: int = Query(1, ge=1),
    user: dict = Depends(require_feature("search")),
):
    return await security_master.search_catalog(
        q=q, exchange=exchange, asset_class=asset_class,
        source=source, advanced=advanced, min_dividend=min_dividend, page=page,
    )


@router.get("/facets")
async def catalog_facets(
    source: Optional[str] = None,
    advanced: bool = False,
    user: dict = Depends(require_feature("search")),
):
    """Exchange + asset-class chips (with counts) for the Explore filters."""
    return await security_master.facets(source=source, advanced=advanced)
