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
    # Grace window after a refresh token is rotated during which re-presenting it is
    # treated as a benign concurrent/duplicate refresh (a cold client firing several
    # queries at once) rather than a replay attack. Outside this window it is a replay.
    refresh_rotation_grace_seconds: int = 10

    # Comma-separated; declared as str so pydantic-settings doesn't try JSON-decoding.
    apple_bundle_ids_csv: str = Field(default="", alias="APPLE_BUNDLE_IDS")
    google_client_ids_csv: str = Field(default="", alias="GOOGLE_CLIENT_IDS")

    # Google Health API OAuth + sync (replaces legacy Fitbit Web API).
    # Standard Google OAuth 2.0; data from the user's Fitbit account via Google.
    google_health_client_id: str = Field(default="", description="Google Health OAuth client ID.")
    google_health_client_secret: str = Field(
        default="", description="Google Health OAuth client secret."
    )
    google_health_redirect_uri: str = "https://app.example.com/integrations/health/callback"

    # Open Food Facts. Live barcode fallback uses the public API; bulk ingest
    # reads the nightly JSONL dump (path/URL configured at run time, not here).
    # ``openfoodfacts_base_url`` optionally overrides the live API host (staging).
    openfoodfacts_base_url: str = Field(
        default="", description="Override for the Open Food Facts API host (staging/testing)."
    )

    # USDA FoodData Central bulk ingest. Only a data.gov API key is needed for the
    # incremental API path; the bulk CSV download (the default ingest route) needs
    # no key. Empty disables the API-key-only paths.
    usda_fdc_api_key: str = Field(
        default="", description="data.gov API key for USDA FoodData Central (optional)."
    )

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
