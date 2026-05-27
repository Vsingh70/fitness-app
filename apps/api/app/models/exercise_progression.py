from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base


class ExerciseProgression(Base):
    __tablename__ = "exercise_progression"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # PR-detection state.
    best_e1rm_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    best_reps_bodyweight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_pace_seconds_per_km: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)

    # Progression-engine rolling state (linear + double progression).
    current_top_set_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    current_target_reps_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_target_reps_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecutive_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_progression_user_ex"),)
