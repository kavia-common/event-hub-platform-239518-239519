from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server / URLs (some come from template .env)
    backend_url: str | None = Field(default=None, alias="BACKEND_URL")
    frontend_url: str | None = Field(default=None, alias="FRONTEND_URL")
    site_url: str | None = Field(default=None, alias="SITE_URL")

    # CORS
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    allowed_headers: str = Field(default="*", alias="ALLOWED_HEADERS")
    allowed_methods: str = Field(default="*", alias="ALLOWED_METHODS")
    cors_max_age: int = Field(default=3600, alias="CORS_MAX_AGE")

    # Auth
    jwt_secret: str = Field(default="CHANGE_ME", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="event-hub-platform", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="event-hub-platform", alias="JWT_AUDIENCE")
    access_token_exp_minutes: int = Field(default=60 * 24 * 7, alias="ACCESS_TOKEN_EXP_MINUTES")

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        alias="DATABASE_URL",
        description="SQLAlchemy URL (async-friendly psycopg driver).",
    )

    # Misc
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a safe subset of settings for debugging/logging."""
        return {
            "backend_url": self.backend_url,
            "frontend_url": self.frontend_url,
            "site_url": self.site_url,
            "allowed_origins": self.allowed_origins,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
            "access_token_exp_minutes": self.access_token_exp_minutes,
        }


@lru_cache
def get_settings() -> Settings:
    """Singleton settings accessor."""
    return Settings()
