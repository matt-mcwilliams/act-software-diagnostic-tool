from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_prefix="ACT_API_",
        extra="ignore",
    )

    app_name: str = "ACT Adaptive API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    auth_jwt_secret: str | None = None
    auth_jwt_issuer: str | None = None
    auth_jwt_audience: str = "authenticated"
    allow_test_user: bool = False
    database_url: str | None = None
    export_pseudonym_secret: str | None = None
    rate_limit_requests: int = Field(default=120, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)


@lru_cache
def get_settings() -> Settings:
    return Settings()
