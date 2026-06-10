from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps.auth import require_role
from app.models.event import Event
from app.models.moderation import ModerationReport
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


# PUBLIC_INTERFACE
@router.get(
    "/stats",
    response_model=dict,
    summary="Admin stats",
    description="Returns basic platform counts for admin dashboard.",
)
async def stats(
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return basic stats used by the frontend admin page."""
    user_count_res = await db.execute(select(func.count()).select_from(User))
    event_count_res = await db.execute(select(func.count()).select_from(Event).where(Event.is_deleted.is_(False)))
    report_count_res = await db.execute(select(func.count()).select_from(ModerationReport).where(ModerationReport.status == "open"))

    return {
        "user_count": int(user_count_res.scalar_one() or 0),
        "event_count": int(event_count_res.scalar_one() or 0),
        "report_count": int(report_count_res.scalar_one() or 0),
    }
