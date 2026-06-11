from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MealType


class MealItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meal_id: UUID
    food_id: UUID
    grams: Decimal
    kcal: Decimal | None
    protein_g: Decimal | None
    carbs_g: Decimal | None
    fat_g: Decimal | None
    fiber_g: Decimal | None
    created_at: datetime


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    eaten_at: datetime
    meal_type: MealType
    notes: str | None
    photo_url: str | None
    items: list[MealItemResponse]
    created_at: datetime


class MealList(BaseModel):
    items: list[MealResponse]


class MealCreate(BaseModel):
    eaten_at: datetime
    meal_type: MealType
    notes: str | None = None
    photo_url: str | None = None


class MealUpdate(BaseModel):
    eaten_at: datetime | None = None
    meal_type: MealType | None = None
    notes: str | None = None
    photo_url: str | None = None


class MealItemCreate(BaseModel):
    food_id: UUID
    grams: Decimal = Field(gt=Decimal("0"))


class MealItemUpdate(BaseModel):
    food_id: UUID | None = None
    grams: Decimal | None = Field(default=None, gt=Decimal("0"))


# Daily summary -------------------------------------------------------------


class DayMacros(BaseModel):
    kcal: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal


class DayPerMeal(BaseModel):
    meal_id: UUID
    meal_type: MealType
    eaten_at: datetime
    totals: DayMacros
    items: list[MealItemResponse]


class DaySummaryResponse(BaseModel):
    date: date
    totals: DayMacros
    per_meal: list[DayPerMeal]


# Meal plans ----------------------------------------------------------------


class MealPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    target_kcal: Decimal
    target_protein_g: Decimal
    target_carbs_g: Decimal
    target_fat_g: Decimal
    target_fiber_g: Decimal | None
    days: dict[str, Any]
    is_active: bool
    activated_at: datetime | None
    created_at: datetime


class MealPlanList(BaseModel):
    items: list[MealPlanResponse]


class MealPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    target_kcal: Decimal = Field(ge=Decimal("0"))
    target_protein_g: Decimal = Field(ge=Decimal("0"))
    target_carbs_g: Decimal = Field(ge=Decimal("0"))
    target_fat_g: Decimal = Field(ge=Decimal("0"))
    target_fiber_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    days: dict[str, Any] | None = None


class MealPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    target_kcal: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_protein_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_carbs_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fat_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fiber_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    days: dict[str, Any] | None = None


class MealPlanTargets(BaseModel):
    target_kcal: Decimal
    target_protein_g: Decimal
    target_carbs_g: Decimal
    target_fat_g: Decimal


class RemainingMacros(BaseModel):
    kcal: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


class ActivePlanProgress(BaseModel):
    plan: MealPlanResponse
    consumed: DayMacros
    remaining: RemainingMacros
    date: date


# Body metrics --------------------------------------------------------------


class BodyMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: datetime
    weight_kg: Decimal | None
    body_fat_pct: Decimal | None
    created_at: datetime


class BodyMetricList(BaseModel):
    items: list[BodyMetricResponse]


class BodyMetricCreate(BaseModel):
    recorded_at: datetime
    weight_kg: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("500"))
    body_fat_pct: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
