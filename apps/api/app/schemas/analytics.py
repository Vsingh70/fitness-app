from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    AnalyticsInsightKind,
    AnalyticsInsightSeverity,
    Equipment,
    MovementPattern,
    Muscle,
    RecommendationKind,
)


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


class InsightUpdate(BaseModel):
    """Partial update for an insight. Currently only dismissal state is mutable.

    ``dismissed`` is the convenience flag the client sends:
    - ``true``  -> set ``dismissed_at`` to now (if not already dismissed).
    - ``false`` -> clear ``dismissed_at`` (un-dismiss / restore).
    """

    dismissed: bool


class InsightList(BaseModel):
    items: list[InsightResponse]
    next_cursor: str | None = None


class RecomputeInsightsResponse(BaseModel):
    count: int


# Per-exercise analytics ---------------------------------------------------


class TimeSeriesPointResponse(BaseModel):
    session_date: date
    value: Decimal


class ScatterPointResponse(BaseModel):
    session_date: date
    weight_kg: Decimal
    reps: int
    rpe: Decimal | None
    is_pr: bool


class PRRowResponse(BaseModel):
    session_date: date
    weight_kg: Decimal
    reps: int
    e1rm_kg: Decimal


class PredictedNextSessionResponse(BaseModel):
    has_prediction: bool
    suggested_weight_kg: Decimal | None
    suggested_reps_low: int | None
    suggested_reps_high: int | None
    kind: RecommendationKind | None
    rationale_key: str | None
    rationale: str | None
    is_deload: bool
    source: str


class ExerciseSummaryResponse(BaseModel):
    id: UUID
    name: str
    primary_muscle: Muscle
    secondary_muscles: list[Muscle]
    equipment: Equipment
    movement_pattern: MovementPattern


class VariantRowResponse(BaseModel):
    exercise: ExerciseSummaryResponse
    usage_count: int


class ExerciseAnalyticsResponse(BaseModel):
    exercise: ExerciseSummaryResponse
    window: str
    e1rm_series: list[TimeSeriesPointResponse]
    volume_series: list[TimeSeriesPointResponse]
    avg_rpe_series: list[TimeSeriesPointResponse]
    set_scatter: list[ScatterPointResponse]
    recent_prs: list[PRRowResponse]
    predicted_next_session: PredictedNextSessionResponse
    suggested_variants: list[VariantRowResponse]
