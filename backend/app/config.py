from __future__ import annotations

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"

    # JWT / Security
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — comma-separated string in .env, e.g.:
    #   CORS_ORIGINS=http://localhost:5173,http://localhost:5174
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
    CORS_ALLOW_CREDENTIALS: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False

    # File uploads — CV/resume storage directory (relative to cwd or absolute)
    UPLOADS_DIR: str = "uploads"

    # Email notifications — sent as a background task on each new application
    NOTIFICATIONS_ENABLED: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_NAME: str | None = None  # Display name in From header, e.g. "Acme Careers"
    SMTP_NOTIFICATION_TO: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
