from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import SexAtBirth, UnitSystem


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
    auto_push_to_fitbit: bool


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    unit_system: UnitSystem | None = None
    birthdate: date | None = None
    sex_at_birth: SexAtBirth | None = None
    timezone: str | None = Field(default=None, max_length=64)
    height_cm: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("300"))
    auto_push_to_fitbit: bool | None = None
