from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.models.exercise import Exercise

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import BlockKind, SegmentKind, SetType, TrackingType


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

    fitbit_log_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fitbit_pushed_at: Mapped[datetime | None] = mapped_column(
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

    workout_exercises: Mapped[list[WorkoutExercise]] = relationship(
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

    # Block grouping: working-volume rollups, per-muscle analytics, and PR
    # detection count only ``working`` blocks. Warm-up/cooldown blocks of varied
    # movements are logged and visible in history but never counted as volume.
    block_kind: Mapped[BlockKind] = mapped_column(
        SAEnum(BlockKind, name="block_kind", native_enum=True, create_type=False),
        default=BlockKind.working,
        server_default="working",
        nullable=False,
    )
    block_label: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Temporary one-session swap: when set, this row's logged sets credit the
    # substitute exercise and the original (``substituted_for_exercise_id``)
    # pauses — it is neither progressed nor stalled for this slot.
    substituted_for_exercise_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="SET NULL"),
        nullable=True,
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

    session: Mapped[WorkoutSession] = relationship(back_populates="workout_exercises")
    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        foreign_keys=[exercise_id],
        lazy="raise",
    )
    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_index",
    )

    @property
    def exercise_name(self) -> str:
        return self.exercise.name

    @property
    def tracking_type(self) -> TrackingType:
        return self.exercise.tracking_type


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

    # Interval/HIIT round count (``set_type=interval``). One round is described by
    # this set's ``work``/``rest`` segments; analytics read work across rounds.
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    segments: Mapped[list[SetSegment]] = relationship(
        back_populates="set",
        cascade="all, delete-orphan",
        order_by="SetSegment.segment_index",
    )


class SetSegment(Base):
    """Intra-set sub-bout: rest-pause/cluster/myo ``mini_set`` bouts, or interval
    ``work``/``rest`` segments. A normal straight set has zero segments (the
    ``sets`` row carries the values). Total reps for analytics = sum of segment
    reps; interval work time/distance come from ``work`` segments only.
    """

    __tablename__ = "set_segments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    set_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[SegmentKind] = mapped_column(
        SAEnum(SegmentKind, name="segment_kind", native_enum=True, create_type=False),
        nullable=False,
    )

    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    set: Mapped[WorkoutSet] = relationship(back_populates="segments")

    __table_args__ = (
        UniqueConstraint(
            "set_id",
            "segment_index",
            name="uq_set_segments_set_id_segment_index",
        ),
    )
