from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    MealPlanContentMode,
    MealPlanDayRole,
    MealPlanItemUnit,
    MealPlanKind,
    MealPlanTrackingMode,
    MealType,
)


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
    items: list[MealItemResponse]
    created_at: datetime


class MealList(BaseModel):
    items: list[MealResponse]


class MealCreate(BaseModel):
    eaten_at: datetime
    meal_type: MealType
    notes: str | None = None


class MealUpdate(BaseModel):
    eaten_at: datetime | None = None
    meal_type: MealType | None = None
    notes: str | None = None


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


class PlanMacros(BaseModel):
    """Rolled-up totals for an item, a meal, or a day template."""

    kcal: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


class PlanTargets(BaseModel):
    """Effective targets for a day template (per-day override -> plan default ->
    summed-meal totals, per content_mode)."""

    target_kcal: Decimal | None
    target_protein_g: Decimal | None
    target_carbs_g: Decimal | None
    target_fat_g: Decimal | None


# --- nested item ---


class MealPlanItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    food_id: UUID
    amount: Decimal
    unit: MealPlanItemUnit
    serving_id: UUID | None
    grams: Decimal
    kcal: Decimal | None
    protein_g: Decimal | None
    carbs_g: Decimal | None
    fat_g: Decimal | None


class MealPlanItemCreate(BaseModel):
    food_id: UUID
    amount: Decimal = Field(gt=Decimal("0"))
    unit: MealPlanItemUnit = MealPlanItemUnit.g
    serving_id: UUID | None = None


class MealPlanItemPatch(BaseModel):
    food_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))
    unit: MealPlanItemUnit | None = None
    serving_id: UUID | None = None


# --- nested meal ---


class MealPlanMealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slot_index: int
    planned_time: time | None
    items: list[MealPlanItemResponse]
    totals: PlanMacros


class MealPlanMealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slot_index: int = Field(default=0, ge=0)
    planned_time: time | None = None
    items: list[MealPlanItemCreate] = Field(default_factory=list)


class MealPlanMealPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    slot_index: int | None = Field(default=None, ge=0)
    planned_time: time | None = None


# --- nested day template ---


class MealPlanDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    day_role: MealPlanDayRole
    target_kcal: Decimal | None
    target_protein_g: Decimal | None
    target_carbs_g: Decimal | None
    target_fat_g: Decimal | None
    meals: list[MealPlanMealResponse]
    totals: PlanMacros
    effective_targets: PlanTargets


class MealPlanDayCreate(BaseModel):
    day_role: MealPlanDayRole
    target_kcal: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_protein_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_carbs_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fat_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    meals: list[MealPlanMealCreate] = Field(default_factory=list)


class MealPlanDayPatch(BaseModel):
    target_kcal: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_protein_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_carbs_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fat_g: Decimal | None = Field(default=None, ge=Decimal("0"))


# --- plan ---


class MealPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    plan_kind: MealPlanKind
    content_mode: MealPlanContentMode
    tracking_mode: MealPlanTrackingMode
    target_kcal: Decimal | None
    target_protein_g: Decimal | None
    target_carbs_g: Decimal | None
    target_fat_g: Decimal | None
    target_fiber_g: Decimal | None
    synced_to_program: bool
    training_dows: list[int]
    week_resets: bool
    week_start_dow: int
    needs_week_review: bool
    is_active: bool
    activated_at: datetime | None
    created_at: datetime
    day_templates: list[MealPlanDayResponse]


class MealPlanList(BaseModel):
    items: list[MealPlanResponse]


class MealPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    plan_kind: MealPlanKind = MealPlanKind.daily_repeating
    content_mode: MealPlanContentMode = MealPlanContentMode.targets_and_meals
    tracking_mode: MealPlanTrackingMode = MealPlanTrackingMode.macros_and_calories
    target_kcal: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_protein_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_carbs_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fat_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fiber_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    synced_to_program: bool = False
    training_dows: list[int] = Field(default_factory=list)
    week_resets: bool = False
    week_start_dow: int = Field(default=0, ge=0, le=6)
    day_templates: list[MealPlanDayCreate] = Field(default_factory=list)


class MealPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    content_mode: MealPlanContentMode | None = None
    tracking_mode: MealPlanTrackingMode | None = None
    target_kcal: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_protein_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_carbs_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fat_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_fiber_g: Decimal | None = Field(default=None, ge=Decimal("0"))
    synced_to_program: bool | None = None
    training_dows: list[int] | None = None
    week_resets: bool | None = None
    week_start_dow: int | None = Field(default=None, ge=0, le=6)
    # Setting this False clears the weekly-review prompt after the user has
    # reviewed next week's targets.
    needs_week_review: bool | None = None


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


class ResolvedDay(BaseModel):
    """The day template that applies to a given date, with its effective
    targets and planned meals."""

    date: date
    day_role: MealPlanDayRole
    is_training_day: bool | None
    effective_targets: PlanTargets
    tracking_mode: MealPlanTrackingMode
    template: MealPlanDayResponse | None


class ActivePlanProgress(BaseModel):
    plan: MealPlanResponse
    resolved_day: ResolvedDay | None
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
    neck_cm: Decimal | None = None
    waist_cm: Decimal | None = None
    hip_cm: Decimal | None = None
    created_at: datetime


class BodyMetricList(BaseModel):
    items: list[BodyMetricResponse]


class BodyMetricCreate(BaseModel):
    recorded_at: datetime
    weight_kg: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("500"))
    body_fat_pct: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
    neck_cm: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("300"))
    waist_cm: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("300"))
    hip_cm: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("300"))


# Body-metrics trend --------------------------------------------------------


class BodyMetricTrendPoint(BaseModel):
    """One ISO-week bucket. `value` is the raw weekly mean of the metric;
    `moving_average` is the trailing moving average across weekly means.
    Both are null for weeks with no observation of the metric.
    """

    iso_year: int
    iso_week: int
    week_start: date
    value: Decimal | None
    moving_average: Decimal | None


class BodyMetricTrendSeries(BaseModel):
    metric: str
    points: list[BodyMetricTrendPoint]


class BodyMetricTrendResponse(BaseModel):
    weeks: int
    window: int
    series: list[BodyMetricTrendSeries]
