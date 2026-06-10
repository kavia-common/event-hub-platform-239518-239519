from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve current user from Bearer token."""
    if creds is None or not creds.scheme.lower() == "bearer":
        raise unauthorized()

    try:
        token_data = decode_token(creds.credentials)
    except Exception:
        raise unauthorized("Invalid token")

    user_id = token_data.sub
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized("User inactive or not found")
    if user.is_banned:
        raise forbidden("User is banned")
    return user


def require_role(*roles: str):
    """Dependency factory to enforce user role membership."""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden("Insufficient role")
        return user

    return _dep
