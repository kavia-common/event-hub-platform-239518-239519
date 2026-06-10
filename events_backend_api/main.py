"""
FastAPI backend for the Event Hub Platform.

Implements:
- Auth (register/login) with JWT bearer tokens
- User profile (me)
- Events CRUD + feed/search filtering
- RSVP
- Likes/comments/shares
- Event chat
- Notifications
- Moderation/reporting + admin endpoints

The service is backed by the Postgres schema defined in:
event-hub-platform-239518-258817/events_database/001_init_schema.sql
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import admin, auth, chat, events, moderation, notifications, users
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    openapi_tags = [
        {"name": "Health", "description": "Service health and diagnostics."},
        {"name": "Auth", "description": "User registration and login."},
        {"name": "Users", "description": "Current user and profile operations."},
        {"name": "Events", "description": "Event CRUD, feed/search, RSVP, and engagement."},
        {"name": "Chat", "description": "Event-level group chat messages."},
        {"name": "Notifications", "description": "User notifications."},
        {"name": "Moderation", "description": "Reporting and moderation workflows."},
        {"name": "Admin", "description": "Admin-only stats and audit endpoints."},
    ]

    app = FastAPI(
        title="Event Hub Platform API",
        description=(
            "Backend REST API for the Event Hub Platform.\n\n"
            "Authentication: Bearer JWT via `Authorization: Bearer <token>`.\n\n"
            "Real-time: This version provides chat as REST endpoints (polling). "
            "A WebSocket endpoint can be added later if needed."
        ),
        version="0.1.0",
        openapi_tags=openapi_tags,
    )

    # CORS
    allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    allowed_headers = [h.strip() for h in settings.allowed_headers.split(",") if h.strip()]
    allowed_methods = [m.strip() for m in settings.allowed_methods.split(",") if m.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=allowed_methods or ["*"],
        allow_headers=allowed_headers or ["*"],
        max_age=settings.cors_max_age,
    )

    # Routers
    app.include_router(health_router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(events.router)
    app.include_router(chat.router)
    app.include_router(notifications.router)
    app.include_router(moderation.router)
    app.include_router(admin.router)

    return app


app = create_app()
