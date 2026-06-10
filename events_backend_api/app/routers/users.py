from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps.auth import get_current_user
from app.models.user import User, UserProfile
from app.schemas import UpdateMeRequest, UserMe

router = APIRouter(prefix="/users", tags=["Users"])


def _to_user_me(user: User, profile: UserProfile | None) -> UserMe:
    return UserMe(
        id=str(user.id),
        email=user.email,
        display_name=profile.display_name if profile else None,
        bio=profile.bio if profile else None,
        role=user.role,
    )


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserMe,
    summary="Get current user",
    description="Returns the authenticated user's core fields and profile.",
)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMe:
    """Return the current user and profile info."""
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = res.scalar_one_or_none()
    return _to_user_me(user, profile)


# PUBLIC_INTERFACE
@router.patch(
    "/me",
    response_model=UserMe,
    summary="Update current user's profile",
    description="Updates display_name and/or bio for the authenticated user.",
)
async def patch_me(
    req: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMe:
    """Update profile fields for the current user."""
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = res.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id, display_name=None, bio=None, avatar_url=None)
        db.add(profile)

    if req.display_name is not None:
        profile.display_name = req.display_name
    if req.bio is not None:
        profile.bio = req.bio

    await db.commit()
    await db.refresh(profile)
    return _to_user_me(user, profile)
