from functools import cached_property, lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    database_url: str = Field(
        default="postgresql+asyncpg://gym:gym@localhost:5433/gym",
        description="SQLAlchemy async URL. Must use the asyncpg driver.",
    )
    redis_url: str = "redis://localhost:6379/0"
    ollama_url: str = "http://localhost:11434"

    git_sha: str = Field(default="dev", description="Build-time git sha; baked in by Dockerfile.")

    # Auth
    jwt_secret: str = Field(default="dev-only-change-me", description="HS256 signing secret.")
    jwt_access_ttl_minutes: int = 15
    refresh_ttl_days: int = 60

    # Comma-separated; declared as str so pydantic-settings doesn't try JSON-decoding.
    apple_bundle_ids_csv: str = Field(default="", alias="APPLE_BUNDLE_IDS")
    google_client_ids_csv: str = Field(default="", alias="GOOGLE_CLIENT_IDS")

    @cached_property
    def apple_bundle_ids(self) -> list[str]:
        return _split_csv(self.apple_bundle_ids_csv)

    @cached_property
    def google_client_ids(self) -> list[str]:
        return _split_csv(self.google_client_ids_csv)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
