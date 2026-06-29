from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from app.models.enums import (
    BlockKind,
    IntensityMode,
    PeriodizationMode,
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
    RepMode,
    ScheduledWorkoutStatus,
    TemplateVisibility,
)


class ProgramTemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str | None
    author: str | None
    goal: ProgramGoal
    microcycle_length: int
    mesocycle_length_microcycles: int
    owner_id: UUID | None
    visibility: TemplateVisibility | None


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
    rep_mode: RepMode
    progression_strategy: ProgressionStrategy
    notes: str | None
    block_kind: BlockKind
    block_label: str | None


class ProgramDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slot_index: int
    name: str
    is_rest_day: bool
    exercises: list[ProgramDayExerciseResponse]


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    goal: ProgramGoal
    microcycle_length: int
    source: ProgramSource
    template_id: UUID | None
    is_active: bool
    activated_at: datetime | None
    mesocycle_length_microcycles: int
    auto_deload: bool
    periodization_mode: PeriodizationMode
    auto_deload_on_stall: bool
    intensity_mode: IntensityMode
    days: list[ProgramDayResponse]
    created_at: datetime


class ProgramListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    goal: ProgramGoal
    microcycle_length: int
    mesocycle_length_microcycles: int
    source: ProgramSource
    is_active: bool
    activated_at: datetime | None
    created_at: datetime


class ProgramList(BaseModel):
    items: list[ProgramListItem]
    next_cursor: str | None


# Mutations -----------------------------------------------------------------


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    goal: ProgramGoal
    periodization_mode: PeriodizationMode = PeriodizationMode.block
    auto_deload_on_stall: bool = True
    intensity_mode: IntensityMode = IntensityMode.rpe


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    goal: ProgramGoal | None = None
    mesocycle_length_microcycles: int | None = Field(default=None, ge=1)
    auto_deload: bool | None = None
    periodization_mode: PeriodizationMode | None = None
    auto_deload_on_stall: bool | None = None
    intensity_mode: IntensityMode | None = None


class ProgramDayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_rest_day: bool = False


class ProgramDayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_rest_day: bool | None = None


class SlotReorderRequest(BaseModel):
    slot_ids: list[UUID]  # full ordered list of this program's slot ids


class ProgramPositionResponse(BaseModel):
    current_slot_index: int
    current_microcycle_number: int
    current_repetition: int
    mesocycle_length_microcycles: int
    in_deload: bool
    today_slot: ProgramDayResponse | None  # null if program has no slots
    is_rest_day: bool
    next_training_slot: ProgramDayResponse | None  # the next training slot if today is rest


class DuplicateProgramResponse(BaseModel):
    program: ProgramResponse


class SaveAsTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    visibility: TemplateVisibility = TemplateVisibility.private


class SaveAsTemplateResponse(BaseModel):
    template: ProgramTemplateSummary


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
    rep_mode: RepMode = RepMode.range
    progression_strategy: ProgressionStrategy = ProgressionStrategy.none
    notes: str | None = None
    block_kind: BlockKind = BlockKind.working
    block_label: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _validate_rep_range(self) -> "ProgramDayExerciseCreate":
        if self.target_reps_high is not None and (
            self.target_reps_low is None or self.target_reps_high < self.target_reps_low
        ):
            # PydanticCustomError keeps errors() JSON-serializable (a bare
            # ValueError lands in ctx and breaks the validation envelope).
            raise PydanticCustomError(
                "rep_range",
                "target_reps_high requires target_reps_low <= target_reps_high.",
            )
        return self


class ProgramDayExerciseUpdate(BaseModel):
    target_sets: int | None = Field(default=None, ge=1, le=20)
    target_reps_low: int | None = Field(default=None, ge=1)
    target_reps_high: int | None = Field(default=None, ge=1)
    target_rpe_low: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rpe_high: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    target_rir_low: int | None = Field(default=None, ge=0, le=10)
    target_rir_high: int | None = Field(default=None, ge=0, le=10)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    rep_mode: RepMode | None = None
    progression_strategy: ProgressionStrategy | None = None
    notes: str | None = None
    position: int | None = Field(default=None, ge=0)
    block_kind: BlockKind | None = None
    block_label: str | None = Field(default=None, max_length=80)


# Scheduled workouts --------------------------------------------------------


class ScheduledWorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID | None
    program_day_id: UUID | None
    scheduled_for: date | None
    status: ScheduledWorkoutStatus
    microcycle_number: int | None
    repetition: int | None
    is_deload: bool


# Per-lift reactive deload --------------------------------------------------


class ExerciseDeloadResponse(BaseModel):
    exercise_id: UUID
    prior_weight_kg: Decimal | None
    new_weight_kg: Decimal | None
    applied: bool
