from datetime import date as date_cls
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Band = Literal["low", "moderate", "high"]


class ReadinessDay(BaseModel):
    date: date_cls
    score: int | None
    band: Band | None
    steps: int | None = None
    sleep_minutes: int | None = None
    resting_hr: int | None = None
    hrv_ms: Decimal | None = None


class ReadinessTodayResponse(BaseModel):
    date: date_cls
    score: int | None
    band: Band | None
    has_data: bool


class ReadinessHistoryResponse(BaseModel):
    items: list[ReadinessDay]


class ReduceTodayVolumeResponse(BaseModel):
    affected_count: int
    affected_scheduled_workout_ids: list[str]


class RevertTodayVolumeRequest(BaseModel):
    scheduled_workout_ids: list[str]


class RevertTodayVolumeResponse(BaseModel):
    affected_count: int
