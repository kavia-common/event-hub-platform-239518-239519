from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address.")
    password: str = Field(..., min_length=6, description="User password (min 6 chars).")
    display_name: str | None = Field(default=None, description="Optional display name.")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class UserMe(BaseModel):
    id: str = Field(..., description="User ID (uuid).")
    email: str = Field(..., description="Email.")
    display_name: str | None = Field(default=None, description="Display name.")
    bio: str | None = Field(default=None, description="Bio.")
    role: str | None = Field(default=None, description="Role (user/moderator/admin).")


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, description="Display name.")
    bio: str | None = Field(default=None, description="Bio.")


class Paginated(BaseModel):
    items: list = Field(default_factory=list, description="List of items.")


class EventCreateRequest(BaseModel):
    title: str = Field(..., description="Event title.")
    description: str = Field(..., description="Event description.")
    category: str | None = Field(default=None, description="Event category.")
    start_time: datetime | None = Field(default=None, description="Start time (ISO 8601).")
    end_time: datetime | None = Field(default=None, description="End time (ISO 8601).")
    location_name: str | None = Field(default=None, description="Human readable location.")
    latitude: float | None = Field(default=None, description="Latitude.")
    longitude: float | None = Field(default=None, description="Longitude.")
    visibility: Literal["public", "unlisted", "private"] | None = Field(default="public", description="Visibility.")
    capacity: int | None = Field(default=None, ge=0, description="Optional capacity.")


class EventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, description="Event title.")
    description: str | None = Field(default=None, description="Event description.")
    category: str | None = Field(default=None, description="Event category.")
    start_time: datetime | None = Field(default=None, description="Start time (ISO 8601).")
    end_time: datetime | None = Field(default=None, description="End time (ISO 8601).")
    location_name: str | None = Field(default=None, description="Location name.")
    latitude: float | None = Field(default=None, description="Latitude.")
    longitude: float | None = Field(default=None, description="Longitude.")
    visibility: Literal["public", "unlisted", "private"] | None = Field(default=None, description="Visibility.")
    capacity: int | None = Field(default=None, ge=0, description="Capacity.")


class RSVPRequest(BaseModel):
    status: Literal["going", "interested", "not_going"] = Field(..., description="RSVP status.")


class CommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, description="Comment body.")


class CommentItem(BaseModel):
    id: str
    body: str
    author_display_name: str | None = None
    created_at: datetime | None = None


class EventSummary(BaseModel):
    id: str
    title: str
    description: str
    category: str | None = None
    start_time: datetime | None = None
    location_name: str | None = None
    like_count: int | None = 0
    comment_count: int | None = 0
    rsvp_counts: dict | None = None


class EventDetails(EventSummary):
    viewer_has_liked: bool | None = False
    comments: list[CommentItem] | None = None


class ChatMessageCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, description="Message body.")


class ChatMessageItem(BaseModel):
    id: str
    body: str
    author_display_name: str | None = None
    created_at: datetime | None = None


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str | None = None
    body: str
    created_at: datetime | None = None


class ModerationReportCreateRequest(BaseModel):
    target_type: str = Field(..., description="Target type: event/comment/chat_message/user.")
    target_id: str = Field(..., description="Target ID (uuid).")
    reason: str = Field(..., description="Reason.")
    details: str | None = Field(default=None, description="Optional details.")


class ModerationReportItem(BaseModel):
    id: str
    target_type: str
    target_id: str
    reason: str
    created_at: datetime | None = None
    status: str | None = None


class ResolveReportRequest(BaseModel):
    action: str = Field(..., description="resolved or dismissed (or other future action).")
    note: str | None = Field(default=None, description="Optional moderator note.")
