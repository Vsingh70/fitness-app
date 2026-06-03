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
    jwt_secret_previous: str | None = Field(
        default=None,
        description=(
            "Previous HS256 signing secret kept valid during rotation. When set, access "
            "tokens that fail to verify against jwt_secret are retried against this value "
            "so in-flight tokens survive a secret rotation."
        ),
    )
    jwt_access_ttl_minutes: int = 15
    refresh_ttl_days: int = 60

    # Comma-separated; declared as str so pydantic-settings doesn't try JSON-decoding.
    apple_bundle_ids_csv: str = Field(default="", alias="APPLE_BUNDLE_IDS")
    google_client_ids_csv: str = Field(default="", alias="GOOGLE_CLIENT_IDS")

    # Meal photo storage + signed URLs
    meal_photo_root: str = Field(
        default="/var/lib/gymapp/meal-photos",
        description="Filesystem root for uploaded meal photos.",
    )
    meal_photo_signing_secret: str = Field(
        default="dev-photo-secret-change-me",
        description="HMAC secret for signed meal-photo URLs.",
    )
    meal_photo_url_ttl_seconds: int = 3600

    # Ollama vision model for photo recognition.
    ollama_vision_model: str = "llava:13b"

    # Fitbit OAuth + sync
    fitbit_client_id: str = Field(default="", description="Fitbit OAuth client ID.")
    fitbit_client_secret: str = Field(default="", description="Fitbit OAuth client secret.")
    fitbit_redirect_uri: str = "https://app.example.com/integrations/fitbit/callback"
    # 32-byte hex (64 chars) or url-safe base64 key for libsodium secret-box.
    fitbit_token_key: str = Field(
        default="0" * 64,
        description="Hex-encoded 32-byte key for encrypting Fitbit tokens at rest.",
    )
    fitbit_webhook_subscriber_verification: str = Field(
        default="dev-fitbit-webhook-verification",
        description="Fitbit subscriber verification code used for the GET handshake.",
    )
    fitbit_webhook_signing_secret: str = Field(
        default="",
        description="Fitbit client secret used to verify webhook HMAC headers.",
    )

    # Observability
    metrics_token: str = Field(
        default="",
        description="Bearer token required on GET /metrics. Empty disables the endpoint.",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        description="OTLP HTTP endpoint for traces. Empty disables tracing.",
    )
    otel_service_name: str = "gymapp-api"
    otel_sample_ratio: float = Field(
        default=0.1,
        description="Baseline trace sample ratio. Errors are always sampled separately.",
    )

    @cached_property
    def apple_bundle_ids(self) -> list[str]:
        return _split_csv(self.apple_bundle_ids_csv)

    @cached_property
    def google_client_ids(self) -> list[str]:
        return _split_csv(self.google_client_ids_csv)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
