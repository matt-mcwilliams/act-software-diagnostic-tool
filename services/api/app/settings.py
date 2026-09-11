from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
