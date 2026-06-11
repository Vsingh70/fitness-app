from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FoodSource, MealPlanItemUnit, ServingUnit


class FoodServingResponse(BaseModel):
    """A named serving (e.g. "1 cup", "100 g") with its resolved gram weight.

    Downstream meal entry uses ``grams`` to convert any selected serving back to
    grams for the per-100g macro math on the parent food.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    metric_amount: Decimal | None
    metric_unit: ServingUnit | None
    grams: Decimal | None
    is_default: bool


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
    servings: list[FoodServingResponse] = []


class FoodList(BaseModel):
    items: list[FoodResponse]
    next_cursor: str | None = None


class RecentFoodResponse(BaseModel):
    """A previously-logged food, with enough to render a one-tap "recent chip"
    (name + kcal) and reproduce the user's most recent logging of it.

    ``last_amount`` / ``last_unit`` / ``last_serving_id`` mirror the most recent
    ``meal_items`` row for this food so the client can re-log it in one tap.
    ``last_kcal`` … ``last_fat_g`` are that row's denormalized macros (for the
    chip's kcal figure without re-resolving from the food's per-100g values).
    """

    food_id: UUID
    name: str
    brand: str | None
    source: FoodSource
    log_count: int
    last_eaten_at: datetime
    last_amount: Decimal | None
    last_unit: MealPlanItemUnit
    last_serving_id: UUID | None
    last_grams: Decimal
    last_kcal: Decimal | None
    last_protein_g: Decimal | None
    last_carbs_g: Decimal | None
    last_fat_g: Decimal | None


class RecentFoodList(BaseModel):
    items: list[RecentFoodResponse]


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
