from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base
from app.models.enums import ScheduledWorkoutStatus


class ScheduledWorkout(Base):
    __tablename__ = "scheduled_workouts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
    )
    program_day_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("program_days.id", ondelete="SET NULL"),
        nullable=True,
    )

    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[ScheduledWorkoutStatus] = mapped_column(
        SAEnum(
            ScheduledWorkoutStatus,
            name="scheduled_workout_status",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=ScheduledWorkoutStatus.planned,
    )

    microcycle_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repetition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deload: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
