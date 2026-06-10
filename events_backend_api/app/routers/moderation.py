from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import bad_request, not_found
from app.deps.auth import get_current_user, require_role
from app.models.moderation import ModerationAction, ModerationReport
from app.models.user import User
from app.schemas import ModerationReportCreateRequest, ResolveReportRequest

router = APIRouter(prefix="/moderation", tags=["Moderation"])


# PUBLIC_INTERFACE
@router.post(
    "/reports",
    status_code=204,
    summary="Create a moderation report",
    description="Report an event/comment/chat message/user for moderator review.",
)
async def create_report(
    req: ModerationReportCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Create a moderation report."""
    try:
        target_id = uuid.UUID(req.target_id)
    except ValueError:
        raise bad_request("Invalid target_id")

    rpt = ModerationReport(
        reporter_user_id=user.id,
        target_type=req.target_type,
        target_id=target_id,
        reason=req.reason,
        details=req.details,
        status="open",
        resolved_at=None,
        resolved_by_user_id=None,
    )
    db.add(rpt)
    await db.commit()
    return None


# PUBLIC_INTERFACE
@router.get(
    "/reports",
    response_model=dict,
    summary="List moderation reports",
    description="Lists reports (moderator/admin only).",
)
async def list_reports(
    limit: int = Query(default=100, ge=1, le=500),
    _mod: User = Depends(require_role("moderator", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List reports for moderators/admin."""
    res = await db.execute(select(ModerationReport).order_by(desc(ModerationReport.created_at)).limit(limit))
    items = [
        {
            "id": str(r.id),
            "target_type": r.target_type,
            "target_id": str(r.target_id),
            "reason": r.reason,
            "created_at": r.created_at,
            "status": r.status,
        }
        for r in res.scalars().all()
    ]
    return {"items": items}


# PUBLIC_INTERFACE
@router.post(
    "/reports/{report_id}/resolve",
    status_code=204,
    summary="Resolve or dismiss a report",
    description="Marks a report resolved/dismissed and writes a moderation action (moderator/admin only).",
)
async def resolve_report(
    report_id: str,
    req: ResolveReportRequest,
    mod: User = Depends(require_role("moderator", "admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Resolve or dismiss a report."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise bad_request("Invalid report id")

    res = await db.execute(select(ModerationReport).where(ModerationReport.id == rid))
    rpt = res.scalar_one_or_none()
    if rpt is None:
        raise not_found("Report not found")

    action = req.action.strip().lower()
    if action not in ("resolved", "dismissed"):
        raise bad_request("action must be 'resolved' or 'dismissed'")

    rpt.status = action
    rpt.resolved_at = datetime.utcnow()
    rpt.resolved_by_user_id = mod.id

    db.add(
        ModerationAction(
            actor_user_id=mod.id,
            target_type=rpt.target_type,
            target_id=rpt.target_id,
            action="warn" if action == "resolved" else "restore",
            note=req.note,
        )
    )

    await db.commit()
    return None
