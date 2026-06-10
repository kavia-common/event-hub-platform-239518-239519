from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, ping_db

router = APIRouter(tags=["Health"])


# PUBLIC_INTERFACE
@router.get(
    "/healthz",
    summary="Health check",
    description="Simple health check. Includes a DB connectivity probe.",
)
async def healthz(db: AsyncSession = Depends(get_db)) -> dict:
    """Return OK if service (and DB) is reachable."""
    await ping_db(db)
    return {"status": "ok"}
