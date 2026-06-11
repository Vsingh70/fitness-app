from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ScheduledWorkoutStatus


class ScheduledWorkoutSummary(BaseModel):
    """Lightweight row for the calendar."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID | None
    program_day_id: UUID | None
    scheduled_for: date
    status: ScheduledWorkoutStatus
    mesocycle_week: int | None
    is_deload: bool


class ScheduledWorkoutWithDay(ScheduledWorkoutSummary):
    """Calendar view: includes the program day name and exercise count."""

    program_day_name: str | None
    exercise_count: int
    program_name: str | None


class ScheduledWorkoutList(BaseModel):
    items: list[ScheduledWorkoutWithDay]


class ScheduledWorkoutUpdate(BaseModel):
    scheduled_for: date | None = None
    status: ScheduledWorkoutStatus | None = None
    is_deload: bool | None = None
    mesocycle_week: int | None = Field(default=None, ge=1, le=52)
