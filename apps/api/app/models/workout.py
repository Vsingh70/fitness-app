from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import SetType


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_workout_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    bodyweight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    perceived_exertion: Mapped[int | None] = mapped_column(Integer, nullable=True)

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

    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.position",
    )

    __table_args__ = (
        CheckConstraint(
            "perceived_exertion is null or (perceived_exertion between 1 and 10)",
            name="ck_workout_sessions_perceived_exertion_range",
        ),
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    workout_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session: Mapped[WorkoutSession] = relationship(back_populates="workout_exercises")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_index",
    )


class WorkoutSet(Base):
    __tablename__ = "sets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    workout_exercise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[SetType] = mapped_column(
        SAEnum(SetType, name="set_type", native_enum=True, create_type=False),
        default=SetType.working,
        nullable=False,
    )

    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    rir: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_pr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workout_exercise: Mapped[WorkoutExercise] = relationship(back_populates="sets")
