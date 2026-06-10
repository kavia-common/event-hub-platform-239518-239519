from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Decoded token payload fields we care about."""

    sub: str = Field(..., description="User ID (uuid) as string.")
    email: str | None = Field(default=None, description="User email.")
    role: str | None = Field(default=None, description="User role.")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash."""
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(*, subject: str, email: str, role: str) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.access_token_exp_minutes)

    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "sub": subject,
        "email": email,
        "role": role,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT access token, raising jwt exceptions if invalid."""
    settings = get_settings()
    data = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return TokenData.model_validate(data)
