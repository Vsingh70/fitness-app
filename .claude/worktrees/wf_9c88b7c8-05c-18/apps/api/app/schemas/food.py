from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FoodSource


class FoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: FoodSource
    external_id: str | None
    name: str
    brand: str | None
    serving_size_g: Decimal | None
    serving_label: str | None
    kcal_per_100g: Decimal | None
    protein_g_per_100g: Decimal | None
    carbs_g_per_100g: Decimal | None
    fat_g_per_100g: Decimal | None
    fiber_g_per_100g: Decimal | None
    owner_id: UUID | None
    payload: dict[str, Any]
    archived_at: datetime | None
    created_at: datetime


class FoodList(BaseModel):
    items: list[FoodResponse]
    next_cursor: str | None = None


class FoodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    brand: str | None = Field(default=None, max_length=160)
    serving_size_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    serving_label: str | None = None
    kcal_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    protein_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    carbs_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    fat_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    fiber_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    external_id: str | None = Field(default=None, max_length=120)


class FoodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    brand: str | None = Field(default=None, max_length=160)
    serving_size_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    serving_label: str | None = None
    kcal_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    protein_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    carbs_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    fat_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
    fiber_g_per_100g: Decimal | None = Field(default=None, ge=Decimal("0"))
