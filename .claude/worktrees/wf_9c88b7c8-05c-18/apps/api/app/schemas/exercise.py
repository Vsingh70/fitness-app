from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Equipment, MovementPattern, Muscle, TrackingType


class ExerciseBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    primary_muscle: Muscle
    secondary_muscles: list[Muscle] = Field(default_factory=list)
    equipment: Equipment
    movement_pattern: MovementPattern
    tracking_type: TrackingType
    is_unilateral: bool = False
    notes: str | None = None
    cues: str | None = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    primary_muscle: Muscle | None = None
    secondary_muscles: list[Muscle] | None = None
    equipment: Equipment | None = None
    movement_pattern: MovementPattern | None = None
    tracking_type: TrackingType | None = None
    is_unilateral: bool | None = None
    notes: str | None = None
    cues: str | None = None


class ExerciseResponse(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    owner_id: UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExerciseList(BaseModel):
    items: list[ExerciseResponse]
    next_cursor: str | None
