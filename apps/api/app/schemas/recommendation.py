from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RecommendationKind


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scheduled_workout_id: UUID | None
    exercise_id: UUID
    kind: RecommendationKind
    payload: dict[str, Any]
    rationale: str | None
    rationale_key: str | None
    suggested_weight_kg: Decimal | None
    suggested_reps_low: int | None
    suggested_reps_high: int | None
    consumed_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class RecommendationList(BaseModel):
    items: list[RecommendationResponse]
    next_cursor: str | None
