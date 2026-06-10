from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import (
    MealPlanContentMode,
    MealPlanDayRole,
    MealPlanItemUnit,
    MealPlanKind,
    MealPlanTrackingMode,
)


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)

    plan_kind: Mapped[MealPlanKind] = mapped_column(
        SAEnum(MealPlanKind, name="meal_plan_kind", native_enum=True, create_type=False),
        nullable=False,
        default=MealPlanKind.daily_repeating,
    )
    content_mode: Mapped[MealPlanContentMode] = mapped_column(
        SAEnum(
            MealPlanContentMode,
            name="meal_plan_content_mode",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=MealPlanContentMode.targets_and_meals,
    )
    tracking_mode: Mapped[MealPlanTrackingMode] = mapped_column(
        SAEnum(
            MealPlanTrackingMode,
            name="meal_plan_tracking_mode",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=MealPlanTrackingMode.macros_and_calories,
    )

    # Plan-level default targets. Nullable: meals_only plans derive them from
    # the summed foods of each day template.
    target_kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    # training_rest plans.
    synced_to_program: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Manual mapping (synced_to_program=False): which weekdays are training days
    # (0=Monday .. 6=Sunday). Ignored when synced.
    training_dows: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger), nullable=False, default=list
    )

    # weekly plans.
    week_resets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    week_start_dow: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    needs_week_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    day_templates: Mapped[list["MealPlanDay"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="MealPlanDay.day_role",
        lazy="selectin",
    )


class MealPlanDay(Base):
    __tablename__ = "meal_plan_days"
    __table_args__ = (UniqueConstraint("meal_plan_id", "day_role", name="uq_meal_plan_days_role"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    meal_plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_role: Mapped[MealPlanDayRole] = mapped_column(
        SAEnum(MealPlanDayRole, name="meal_plan_day_role", native_enum=True, create_type=False),
        nullable=False,
    )

    # Per-day target overrides of the plan defaults.
    target_kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[MealPlan] = relationship(back_populates="day_templates")
    meals: Mapped[list["MealPlanMeal"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="MealPlanMeal.slot_index",
        lazy="selectin",
    )


class MealPlanMeal(Base):
    __tablename__ = "meal_plan_meals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    meal_plan_day_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meal_plan_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    day: Mapped[MealPlanDay] = relationship(back_populates="meals")
    items: Mapped[list["MealPlanItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        order_by="MealPlanItem.created_at",
        lazy="selectin",
    )


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    meal_plan_meal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meal_plan_meals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[MealPlanItemUnit] = mapped_column(
        SAEnum(MealPlanItemUnit, name="meal_plan_item_unit", native_enum=True, create_type=False),
        nullable=False,
    )
    serving_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("food_servings.id", ondelete="SET NULL"),
        nullable=True,
    )
    grams: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    kcal: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    meal: Mapped[MealPlanMeal] = relationship(back_populates="items")
