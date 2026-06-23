from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import FoodSource, ServingUnit


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    source: Mapped[FoodSource] = mapped_column(
        SAEnum(FoodSource, name="food_source", native_enum=True, create_type=False),
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)

    serving_size_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    serving_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    kcal_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    protein_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    carbs_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fat_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    fiber_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    servings: Mapped[list["FoodServing"]] = relationship(
        "FoodServing",
        back_populates="food",
        cascade="all, delete-orphan",
        order_by="desc(FoodServing.is_default)",
        lazy="selectin",
    )


class FoodServing(Base):
    """A named serving for a food (e.g. "1 cup", "100 g").

    A food can carry several servings, each with a metric gram weight (e.g. OFF's
    ``serving_size`` / ``serving_quantity``, or a USDA portion). We persist them so
    meal entry can offer g / cup / serving and convert any selection back to grams.
    The per-100g macros on ``foods`` stay the canonical math base; a serving only
    carries its resolved gram weight.

    ``grams`` is the resolved gram weight of one of this serving. For an ``ml``
    metric with no density we treat 1 ml as 1 g (water-equivalent) so downstream
    conversion always has a gram figure; this approximation is documented here
    and surfaced via ``metric_unit`` so callers can refine it later.
    """

    __tablename__ = "food_servings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    food_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    metric_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    metric_unit: Mapped[ServingUnit | None] = mapped_column(
        SAEnum(ServingUnit, name="serving_unit", native_enum=True, create_type=False),
        nullable=True,
    )
    grams: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    food: Mapped[Food] = relationship("Food", back_populates="servings")
