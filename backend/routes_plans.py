"""Public plans catalog: limits + capability matrix + card bullet keys."""
from fastapi import APIRouter

from plans import catalog

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/catalog")
async def plans_catalog():
    return {"plans": catalog()}
