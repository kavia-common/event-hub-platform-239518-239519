from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import bad_request, forbidden, not_found
from app.deps.auth import get_current_user
from app.models.event import Event, EventComment, EventLike, EventRSVP, EventShare
from app.models.user import User, UserProfile
from app.schemas import (
    CommentCreateRequest,
    EventCreateRequest,
    EventDetails,
    EventSummary,
    EventUpdateRequest,
    Paginated,
    RSVPRequest,
)

router = APIRouter(prefix="/events", tags=["Events"])


def _event_summary_row_to_model(row: Any) -> EventSummary:
    # row = (Event, like_count, comment_count, going_count, interested_count)
    e: Event = row[0]
    like_count = int(row[1] or 0)
    comment_count = int(row[2] or 0)
    going_count = int(row[3] or 0)
    interested_count = int(row[4] or 0)

    return EventSummary(
        id=str(e.id),
        title=e.title,
        description=e.description,
        category=e.category,
        start_time=e.start_time,
        location_name=e.location_name,
        like_count=like_count,
        comment_count=comment_count,
        rsvp_counts={"going": going_count, "interested": interested_count},
    )


async def _ensure_event_visible(db: AsyncSession, event: Event, viewer: User) -> None:
    if event.is_deleted:
        raise not_found("Event not found")
    if event.visibility == "public":
        return
    if event.owner_user_id == viewer.id:
        return
    # For now: unlisted/private are visible only to owner (could expand later)
    raise forbidden("Event not accessible")


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=dict,
    summary="List events (feed/search)",
    description=(
        "Returns a list of events with lightweight engagement counts.\n\n"
        "Query params supported:\n"
        "- q: search query in title/description\n"
        "- category: category filter\n"
        "- start_from, start_to: ISO date bounds for start_time\n"
        "- lat, lng, radius_km: naive bounding-box filter (no PostGIS)\n"
        "- limit: max items"
    ),
)
async def list_events(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    start_from: datetime | None = Query(default=None),
    start_to: datetime | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    radius_km: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List events for the feed/search experience."""
    filters = [Event.is_deleted.is_(False)]
    # Visibility: public OR owned by user
    filters.append(or_(Event.visibility == "public", Event.owner_user_id == user.id))

    if q:
        like = f"%{q}%"
        filters.append(or_(Event.title.ilike(like), Event.description.ilike(like)))
    if category:
        filters.append(Event.category == category)
    if start_from:
        filters.append(Event.start_time >= start_from)
    if start_to:
        filters.append(Event.start_time <= start_to)

    # Bounding-box geo filtering (approx)
    if lat is not None and lng is not None and radius_km is not None and radius_km > 0:
        # 1 deg lat ~ 111km, 1 deg lon ~ 111km*cos(lat)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * max(0.1, abs(__import__("math").cos(__import__("math").radians(lat)))))
        filters.append(and_(Event.latitude.is_not(None), Event.longitude.is_not(None)))
        filters.append(Event.latitude.between(lat - lat_delta, lat + lat_delta))
        filters.append(Event.longitude.between(lng - lon_delta, lng + lon_delta))

    # Aggregate counts
    like_count = select(func.count()).select_from(EventLike).where(EventLike.event_id == Event.id).correlate(Event).scalar_subquery()
    comment_count = (
        select(func.count())
        .select_from(EventComment)
        .where(and_(EventComment.event_id == Event.id, EventComment.is_deleted.is_(False)))
        .correlate(Event)
        .scalar_subquery()
    )
    going_count = (
        select(func.count())
        .select_from(EventRSVP)
        .where(and_(EventRSVP.event_id == Event.id, EventRSVP.status == "going"))
        .correlate(Event)
        .scalar_subquery()
    )
    interested_count = (
        select(func.count())
        .select_from(EventRSVP)
        .where(and_(EventRSVP.event_id == Event.id, EventRSVP.status == "interested"))
        .correlate(Event)
        .scalar_subquery()
    )

    stmt = (
        select(Event, like_count, comment_count, going_count, interested_count)
        .where(and_(*filters))
        .order_by(desc(Event.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    items = [_event_summary_row_to_model(r) for r in res.all()]
    return {"items": [i.model_dump() for i in items]}


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=dict,
    summary="Create event",
    description="Creates a new event owned by the authenticated user.",
)
async def create_event(
    req: EventCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create an event."""
    e = Event(
        owner_user_id=user.id,
        title=req.title,
        description=req.description,
        category=req.category,
        start_time=req.start_time,
        end_time=req.end_time,
        location_name=req.location_name,
        latitude=req.latitude,
        longitude=req.longitude,
        visibility=req.visibility or "public",
        capacity=req.capacity,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)

    summary = EventSummary(
        id=str(e.id),
        title=e.title,
        description=e.description,
        category=e.category,
        start_time=e.start_time,
        location_name=e.location_name,
        like_count=0,
        comment_count=0,
        rsvp_counts={"going": 0, "interested": 0},
    )
    return {"id": str(e.id), **summary.model_dump()}


# PUBLIC_INTERFACE
@router.get(
    "/{event_id}",
    response_model=EventDetails,
    summary="Get event details",
    description="Returns event summary + viewer engagement + latest comments.",
)
async def get_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventDetails:
    """Fetch event details."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise not_found("Event not found")
    await _ensure_event_visible(db, e, user)

    # counts
    like_count_res = await db.execute(select(func.count()).select_from(EventLike).where(EventLike.event_id == eid))
    like_count = int(like_count_res.scalar_one() or 0)

    comment_count_res = await db.execute(
        select(func.count()).select_from(EventComment).where(and_(EventComment.event_id == eid, EventComment.is_deleted.is_(False)))
    )
    comment_count = int(comment_count_res.scalar_one() or 0)

    rsvp_counts_res = await db.execute(
        select(EventRSVP.status, func.count())
        .where(EventRSVP.event_id == eid)
        .group_by(EventRSVP.status)
    )
    rsvp_counts: dict[str, int] = {"going": 0, "interested": 0}
    for status, cnt in rsvp_counts_res.all():
        rsvp_counts[str(status)] = int(cnt)

    viewer_like_res = await db.execute(
        select(func.count()).select_from(EventLike).where(and_(EventLike.event_id == eid, EventLike.user_id == user.id))
    )
    viewer_has_liked = bool(viewer_like_res.scalar_one() or 0)

    # latest comments (simple)
    comments_res = await db.execute(
        select(EventComment, UserProfile.display_name)
        .join(UserProfile, UserProfile.user_id == EventComment.author_user_id, isouter=True)
        .where(and_(EventComment.event_id == eid, EventComment.is_deleted.is_(False)))
        .order_by(desc(EventComment.created_at))
        .limit(50)
    )
    comments = [
        {
            "id": str(c.id),
            "body": c.body,
            "author_display_name": dn,
            "created_at": c.created_at,
        }
        for (c, dn) in comments_res.all()
    ]

    return EventDetails(
        id=str(e.id),
        title=e.title,
        description=e.description,
        category=e.category,
        start_time=e.start_time,
        location_name=e.location_name,
        like_count=like_count,
        comment_count=comment_count,
        rsvp_counts=rsvp_counts,
        viewer_has_liked=viewer_has_liked,
        comments=comments,
    )


# PUBLIC_INTERFACE
@router.patch(
    "/{event_id}",
    response_model=EventDetails,
    summary="Update event",
    description="Updates mutable fields for an event (owner only).",
)
async def update_event(
    event_id: str,
    req: EventUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventDetails:
    """Update an event (owner only)."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None or e.is_deleted:
        raise not_found("Event not found")
    if e.owner_user_id != user.id:
        raise forbidden("Only owner can edit event")

    for field in (
        "title",
        "description",
        "category",
        "start_time",
        "end_time",
        "location_name",
        "latitude",
        "longitude",
        "visibility",
        "capacity",
    ):
        v = getattr(req, field)
        if v is not None:
            setattr(e, field, v)

    await db.commit()
    return await get_event(event_id=event_id, user=user, db=db)


# PUBLIC_INTERFACE
@router.delete(
    "/{event_id}",
    status_code=204,
    summary="Delete event (soft delete)",
    description="Soft-deletes an event (owner only).",
)
async def delete_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete event."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None or e.is_deleted:
        raise not_found("Event not found")
    if e.owner_user_id != user.id:
        raise forbidden("Only owner can delete event")

    e.is_deleted = True
    e.deleted_at = datetime.utcnow()
    await db.commit()
    return None


# PUBLIC_INTERFACE
@router.put(
    "/{event_id}/rsvp",
    status_code=204,
    summary="Set RSVP status",
    description="Sets RSVP status for the authenticated user.",
)
async def set_rsvp(
    event_id: str,
    req: RSVPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Upsert RSVP."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise not_found("Event not found")
    await _ensure_event_visible(db, e, user)

    r = await db.execute(select(EventRSVP).where(and_(EventRSVP.event_id == eid, EventRSVP.user_id == user.id)))
    existing = r.scalar_one_or_none()
    if existing is None:
        existing = EventRSVP(event_id=eid, user_id=user.id, status=req.status)
        db.add(existing)
    else:
        existing.status = req.status

    await db.commit()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{event_id}/like",
    status_code=204,
    summary="Like event",
    description="Adds a like for the authenticated user.",
)
async def like_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Like event (idempotent)."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")
    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise not_found("Event not found")
    await _ensure_event_visible(db, e, user)

    r = await db.execute(select(EventLike).where(and_(EventLike.event_id == eid, EventLike.user_id == user.id)))
    if r.scalar_one_or_none() is None:
        db.add(EventLike(event_id=eid, user_id=user.id))
        await db.commit()
    return None


# PUBLIC_INTERFACE
@router.delete(
    "/{event_id}/like",
    status_code=204,
    summary="Unlike event",
    description="Removes the user's like (if present).",
)
async def unlike_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unlike event (idempotent)."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    r = await db.execute(select(EventLike).where(and_(EventLike.event_id == eid, EventLike.user_id == user.id)))
    like = r.scalar_one_or_none()
    if like is not None:
        await db.delete(like)
        await db.commit()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{event_id}/comments",
    status_code=204,
    summary="Create comment",
    description="Creates a comment on an event.",
)
async def comment_event(
    event_id: str,
    req: CommentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Create a comment."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")
    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise not_found("Event not found")
    await _ensure_event_visible(db, e, user)

    c = EventComment(event_id=eid, author_user_id=user.id, body=req.body, is_deleted=False, deleted_at=None)
    db.add(c)
    await db.commit()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{event_id}/share",
    status_code=204,
    summary="Share event",
    description="Records a share action for analytics/notifications. Not used by frontend yet.",
)
async def share_event(
    event_id: str,
    channel: str | None = Query(default=None, description="Optional channel (link/copy/twitter/etc)."),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Record share."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    res = await db.execute(select(Event).where(Event.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise not_found("Event not found")
    await _ensure_event_visible(db, e, user)

    db.add(EventShare(event_id=eid, user_id=user.id, channel=channel))
    await db.commit()
    return None
