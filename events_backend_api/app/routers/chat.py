from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import bad_request, not_found
from app.deps.auth import get_current_user
from app.models.event import Event, EventChatMessage, EventChatRoom
from app.models.user import User, UserProfile
from app.schemas import ChatMessageCreateRequest

router = APIRouter(prefix="/events", tags=["Chat"])


async def _get_or_create_room(db: AsyncSession, event_id: uuid.UUID) -> EventChatRoom:
    res = await db.execute(select(EventChatRoom).where(EventChatRoom.event_id == event_id))
    room = res.scalar_one_or_none()
    if room is None:
        room = EventChatRoom(event_id=event_id)
        db.add(room)
        await db.flush()
    return room


# PUBLIC_INTERFACE
@router.get(
    "/{event_id}/chat/messages",
    response_model=dict,
    summary="List chat messages",
    description="Lists recent event chat messages (polling).",
)
async def list_chat_messages(
    event_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List event chat messages."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    ev = await db.execute(select(Event).where(and_(Event.id == eid, Event.is_deleted.is_(False))))
    if ev.scalar_one_or_none() is None:
        raise not_found("Event not found")

    room = await _get_or_create_room(db, eid)

    res = await db.execute(
        select(EventChatMessage, UserProfile.display_name)
        .join(UserProfile, UserProfile.user_id == EventChatMessage.author_user_id, isouter=True)
        .where(and_(EventChatMessage.room_id == room.id, EventChatMessage.is_deleted.is_(False)))
        .order_by(desc(EventChatMessage.created_at))
        .limit(limit)
    )
    items = [
        {
            "id": str(m.id),
            "body": m.body,
            "author_display_name": dn,
            "created_at": m.created_at,
        }
        for (m, dn) in res.all()
    ]
    # Return ascending for UI readability
    items.reverse()
    return {"items": items}


# PUBLIC_INTERFACE
@router.post(
    "/{event_id}/chat/messages",
    status_code=204,
    summary="Send chat message",
    description="Posts a message into the event chat room.",
)
async def send_chat_message(
    event_id: str,
    req: ChatMessageCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Send message."""
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        raise bad_request("Invalid event id")

    ev = await db.execute(select(Event).where(and_(Event.id == eid, Event.is_deleted.is_(False))))
    if ev.scalar_one_or_none() is None:
        raise not_found("Event not found")

    room = await _get_or_create_room(db, eid)
    msg = EventChatMessage(
        room_id=room.id,
        event_id=eid,
        author_user_id=user.id,
        body=req.body,
        is_deleted=False,
        deleted_at=None,
    )
    db.add(msg)
    await db.commit()
    return None
