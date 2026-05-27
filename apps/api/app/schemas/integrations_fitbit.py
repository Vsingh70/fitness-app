from datetime import datetime

from pydantic import BaseModel, Field


class FitbitAuthorizeRequest(BaseModel):
    code_challenge: str = Field(min_length=16, max_length=200)
    scopes: list[str] | None = None


class FitbitAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class FitbitCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=500)
    state: str = Field(min_length=1, max_length=2000)
    code_verifier: str = Field(min_length=16, max_length=200)


class FitbitStatusResponse(BaseModel):
    connected: bool
    last_synced_at: datetime | None = None
    last_synced_activity_at: datetime | None = None
    scopes: list[str] = []


class FitbitSyncResponse(BaseModel):
    activities_written: int
    daily_metrics_written: int
