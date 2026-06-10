from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import (
    PeriodizationMode,
    ProgramGoal,
    ProgramSource,
    ProgressionStrategy,
)


class ProgramTemplate(Base):
    __tablename__ = "program_templates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(160), nullable=True)

    goal: Mapped[ProgramGoal] = mapped_column(
        SAEnum(ProgramGoal, name="program_goal", native_enum=True, create_type=False),
        nullable=False,
    )
    weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)

    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    goal: Mapped[ProgramGoal] = mapped_column(
        SAEnum(ProgramGoal, name="program_goal", native_enum=True, create_type=False),
        nullable=False,
    )
    weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)

    source: Mapped[ProgramSource] = mapped_column(
        SAEnum(ProgramSource, name="program_source", native_enum=True, create_type=False),
        nullable=False,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("program_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mesocycle_length_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    auto_deload: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    periodization_mode: Mapped[PeriodizationMode] = mapped_column(
        SAEnum(PeriodizationMode, name="periodization_mode", native_enum=True, create_type=False),
        nullable=False,
        default=PeriodizationMode.block,
        server_default=PeriodizationMode.block.value,
    )
    auto_deload_on_stall: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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

    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.day_index",
    )


class ProgramDay(Base):
    __tablename__ = "program_days"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    program: Mapped[Program] = relationship(back_populates="days")
    exercises: Mapped[list["ProgramDayExercise"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ProgramDayExercise.position",
    )


class ProgramDayExercise(Base):
    __tablename__ = "program_day_exercises"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    program_day_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("program_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    target_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rpe_low: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    target_rpe_high: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    target_rir_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rir_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    progression_strategy: Mapped[ProgressionStrategy] = mapped_column(
        SAEnum(
            ProgressionStrategy,
            name="progression_strategy",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=ProgressionStrategy.none,
    )
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

    day: Mapped[ProgramDay] = relationship(back_populates="exercises")
