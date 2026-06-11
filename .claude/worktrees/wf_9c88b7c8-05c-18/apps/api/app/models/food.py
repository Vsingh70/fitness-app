from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base
from app.models.enums import FoodSource


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
