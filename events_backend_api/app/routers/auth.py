from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import bad_request, unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserProfile
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Register a new user",
    description="Creates a new user (email/password) and returns an access token.",
)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Register a new user and return a JWT access token."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none() is not None:
        raise bad_request("Email already registered")

    user = User(email=req.email, password_hash=hash_password(req.password), role="user", is_active=True, is_banned=False)
    db.add(user)
    await db.flush()  # to get user.id

    profile = UserProfile(user_id=user.id, display_name=req.display_name, bio=None, avatar_url=None)
    db.add(profile)

    await db.commit()

    token = create_access_token(subject=str(user.id), email=user.email, role=user.role)
    return TokenResponse(access_token=token)


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Validates credentials and returns an access token.",
)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Login with email/password and return a JWT access token."""
    res = await db.execute(select(User).where(User.email == req.email))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise unauthorized("Invalid email or password")
    if not user.is_active:
        raise unauthorized("User inactive")
    token = create_access_token(subject=str(user.id), email=user.email, role=user.role)
    return TokenResponse(access_token=token)
