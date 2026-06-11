from datetime import date as date_cls
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import MealPlanItemUnit, MealType


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meal_type: Mapped[MealType] = mapped_column(
        SAEnum(MealType, name="meal_type", native_enum=True, create_type=False),
        nullable=False,
    )
    # Optional user/plan-supplied display name ("Meal 1", "Pre-workout"). Null
    # in flexible mode lets the client fall back to "Meal {index+1}". meal_type
    # stays required for compatibility but the redesign UI ignores it.
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # When a planned meal is materialized via "mark complete", we link back to
    # the plan slot + the date it was logged for. This drives plan adherence,
    # idempotent re-complete (one logged meal per slot/date), and delete-forever.
    source_plan_meal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meal_plan_meals.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_plan_date: Mapped[date_cls | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        order_by="MealItem.created_at",
    )


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    meal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # amount/unit/serving mirror meal_plan_items so flexible tracking can log in
    # g / ml / a named serving. grams stays the resolved canonical value the
    # macro math + daily totals rely on. amount is nullable for back-compat with
    # rows created before 0023 (back-filled to grams there).
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit: Mapped[MealPlanItemUnit] = mapped_column(
        SAEnum(MealPlanItemUnit, name="meal_plan_item_unit", native_enum=True, create_type=False),
        nullable=False,
        default=MealPlanItemUnit.g,
    )
    serving_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("food_servings.id", ondelete="SET NULL"),
        nullable=True,
    )
    grams: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    kcal: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    meal: Mapped[Meal] = relationship(back_populates="items")
