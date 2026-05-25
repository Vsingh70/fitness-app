from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    jwt_secret: str = Field(default="dev-only-change-me", description="Filled in by auth task.")
    apple_client_id: str = ""
    google_client_id: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
