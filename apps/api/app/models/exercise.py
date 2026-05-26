from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import Equipment, MovementPattern, Muscle, TrackingType


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    primary_muscle: Mapped[Muscle] = mapped_column(
        SAEnum(Muscle, name="muscle", native_enum=True, create_type=False),
        nullable=False,
    )
    secondary_muscles: Mapped[list[Muscle]] = mapped_column(
        ARRAY(SAEnum(Muscle, name="muscle", native_enum=True, create_type=False)),
        nullable=False,
        server_default="{}",
    )
    equipment: Mapped[Equipment] = mapped_column(
        SAEnum(Equipment, name="equipment", native_enum=True, create_type=False),
        nullable=False,
    )
    movement_pattern: Mapped[MovementPattern] = mapped_column(
        SAEnum(MovementPattern, name="movement_pattern", native_enum=True, create_type=False),
        nullable=False,
    )
    tracking_type: Mapped[TrackingType] = mapped_column(
        SAEnum(TrackingType, name="tracking_type", native_enum=True, create_type=False),
        nullable=False,
    )

    is_unilateral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cues: Mapped[str | None] = mapped_column(Text, nullable=True)

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User")
