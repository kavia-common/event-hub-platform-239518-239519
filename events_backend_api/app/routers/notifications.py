from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps.auth import get_current_user
from app.models.moderation import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=dict,
    summary="List notifications",
    description="Returns recent notifications for the authenticated user.",
)
async def list_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List notifications."""
    res = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(desc(Notification.created_at)).limit(limit)
    )
    items = [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "created_at": n.created_at,
        }
        for n in res.scalars().all()
    ]
    return {"items": items}
