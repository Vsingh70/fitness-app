from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProgramGoal, ProgramSource, ProgressionStrategy


class ProgramTemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str | None
    author: str | None
    goal: ProgramGoal
    weeks: int
    days_per_week: int


class ProgramTemplateList(BaseModel):
    items: list[ProgramTemplateSummary]


class ProgramTemplateFull(ProgramTemplateSummary):
    data: dict


class ProgramDayExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    position: int
    target_sets: int
    target_reps_low: int | None
    target_reps_high: int | None
    target_rpe_low: Decimal | None
    target_rpe_high: Decimal | None
    target_rir_low: int | None
    target_rir_high: int | None
    rest_seconds: int | None
    progression_strategy: ProgressionStrategy
    notes: str | None


class ProgramDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    day_index: int
    name: str
    exercises: list[ProgramDayExerciseResponse]


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    goal: ProgramGoal
    weeks: int
    days_per_week: int
    source: ProgramSource
    template_id: UUID | None
    days: list[ProgramDayResponse]
    created_at: datetime
