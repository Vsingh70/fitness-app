from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base
from app.models.enums import Muscle


class MuscleVolumeWeekly(Base):
    __tablename__ = "muscle_volume_weekly"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    iso_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    iso_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    muscle: Mapped[Muscle] = mapped_column(
        SAEnum(Muscle, name="muscle", native_enum=True, create_type=False),
        nullable=False,
    )

    working_sets: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False, default=Decimal("0")
    )
    tonnage_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    average_rir: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "iso_year", "iso_week", "muscle", name="uq_mvw_user_week_muscle"
        ),
    )
