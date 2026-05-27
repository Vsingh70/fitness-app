from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    ScheduledWorkoutStatus,
)


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
    data: dict[str, Any]


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
    is_active: bool
    activated_at: datetime | None
    mesocycle_length_weeks: int
    auto_deload: bool
    days: list[ProgramDayResponse]
    created_at: datetime


class ProgramListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    goal: ProgramGoal
    weeks: int
    days_per_week: int
    source: ProgramSource
    is_active: bool
    activated_at: datetime | None
    created_at: datetime


class ProgramList(BaseModel):
    items: list[ProgramListItem]


# Mutations -----------------------------------------------------------------


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    goal: ProgramGoal
    weeks: int = Field(ge=1, le=52)
    days_per_week: int = Field(ge=1, le=7)


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    goal: ProgramGoal | None = None
    weeks: int | None = Field(default=None, ge=1, le=52)
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    mesocycle_length_weeks: int | None = Field(default=None, ge=2, le=12)
    auto_deload: bool | None = None


class ProgramDayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProgramDayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


class ProgramDayExerciseCreate(BaseModel):
    exercise_id: UUID
    target_sets: int = Field(ge=1, le=20)
    target_reps_low: int | None = Field(default=None, ge=1)
    target_reps_high: int | None = Field(default=None, ge=1)
    target_rpe_low: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rpe_high: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rir_low: int | None = Field(default=None, ge=0, le=10)
    target_rir_high: int | None = Field(default=None, ge=0, le=10)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    progression_strategy: ProgressionStrategy = ProgressionStrategy.none
    notes: str | None = None


class ProgramDayExerciseUpdate(BaseModel):
    target_sets: int | None = Field(default=None, ge=1, le=20)
    target_reps_low: int | None = Field(default=None, ge=1)
    target_reps_high: int | None = Field(default=None, ge=1)
    target_rpe_low: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rpe_high: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rir_low: int | None = Field(default=None, ge=0, le=10)
    target_rir_high: int | None = Field(default=None, ge=0, le=10)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    progression_strategy: ProgressionStrategy | None = None
    notes: str | None = None
    position: int | None = Field(default=None, ge=0)


# Activate ------------------------------------------------------------------


class ActivateRequest(BaseModel):
    start_date: date
    weekday_offset: int = Field(
        ge=0, le=6, description="ISO weekday for day_index=0 (0=Monday..6=Sunday)."
    )
    skip_existing: bool = True


class ScheduledWorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID | None
    program_day_id: UUID | None
    scheduled_for: date
    status: ScheduledWorkoutStatus
    mesocycle_week: int | None
    is_deload: bool


class ActivateResponse(BaseModel):
    program: ProgramResponse
    scheduled_count: int
    skipped_count: int


# Mesocycle ----------------------------------------------------------------


class MesocyclePositionResponse(BaseModel):
    mesocycle_length_weeks: int
    auto_deload: bool
    current_week: int | None
    week_in_meso: int | None
    is_deload: bool
    next_week_is_deload: bool


class TriggerDeloadResponse(BaseModel):
    affected_count: int
    affected_dates: list[date]
