from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import NutritionMode, SexAtBirth, UnitSystem


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr | None
    display_name: str | None
    unit_system: UnitSystem
    birthdate: date | None
    sex_at_birth: SexAtBirth | None
    timezone: str
    height_cm: Decimal | None
    # Null until the user picks a nutrition tracking mode in onboarding.
    nutrition_mode: NutritionMode | None


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    unit_system: UnitSystem | None = None
    birthdate: date | None = None
    sex_at_birth: SexAtBirth | None = None
    timezone: str | None = Field(default=None, max_length=64)
    height_cm: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("300"))
    nutrition_mode: NutritionMode | None = None


class PREventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    set_id: UUID
    exercise_id: UUID
    exercise_name: str
    session_id: UUID
    achieved_at: datetime
    weight_kg: Decimal
    reps: int
    e1rm_kg: Decimal
    # e1RM improvement over the user's previous PR for this exercise; null on
    # the first PR for an exercise.
    e1rm_delta_kg: Decimal | None


class PREventList(BaseModel):
    items: list[PREventResponse]
    next_cursor: str | None
