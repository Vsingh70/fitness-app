from datetime import datetime

from pydantic import BaseModel, Field


class HealthAuthorizeRequest(BaseModel):
    code_challenge: str = Field(min_length=16, max_length=200)
    scopes: list[str] | None = None


class HealthAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class HealthCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=500)
    state: str = Field(min_length=1, max_length=2000)
    code_verifier: str = Field(min_length=16, max_length=200)


class HealthStatusResponse(BaseModel):
    connected: bool
    last_synced_at: datetime | None = None
    last_synced_activity_at: datetime | None = None
    scopes: list[str] = []


class HealthSyncResponse(BaseModel):
    weight_written: int
    body_fat_written: int
