from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AnalyticsInsightKind, AnalyticsInsightSeverity, Muscle


class VolumePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iso_year: int
    iso_week: int
    working_sets: Decimal
    tonnage_kg: Decimal
    average_rir: Decimal | None


class VolumeSeries(BaseModel):
    muscle: Muscle
    points: list[VolumePoint]


class VolumeResponse(BaseModel):
    items: list[VolumeSeries]


class CurrentWeekMusclePoint(BaseModel):
    muscle: Muscle
    working_sets: Decimal
    tonnage_kg: Decimal


class CurrentWeekResponse(BaseModel):
    iso_year: int
    iso_week: int
    total_working_sets: Decimal
    total_tonnage_kg: Decimal
    per_muscle: list[CurrentWeekMusclePoint]


# Insights -----------------------------------------------------------------


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: AnalyticsInsightKind
    severity: AnalyticsInsightSeverity
    subject: str | None
    title: str
    body: str | None
    rationale: str | None
    payload: dict[str, Any]
    surfaced_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class InsightList(BaseModel):
    items: list[InsightResponse]
    next_cursor: str | None = None


class RecomputeInsightsResponse(BaseModel):
    count: int
