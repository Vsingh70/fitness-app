from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import NutritionMode, SexAtBirth, UnitSystem

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    apple_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    unit_system: Mapped[UnitSystem] = mapped_column(
        SAEnum(UnitSystem, name="unit_system", native_enum=True),
        default=UnitSystem.imperial,
        nullable=False,
    )
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex_at_birth: Mapped[SexAtBirth | None] = mapped_column(
        SAEnum(SexAtBirth, name="sex_at_birth", native_enum=True),
        nullable=True,
    )
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York", nullable=False)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    auto_push_to_fitbit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Default rest-timer length (seconds) used by the active-session logger when a
    # program exercise has no explicit rest target and no session override is set.
    default_rest_seconds: Mapped[int] = mapped_column(
        Integer, default=90, server_default="90", nullable=False
    )

    # Null = user hasn't onboarded into the nutrition redesign yet; the client
    # shows first-run onboarding (flexible vs plan) until this is set.
    nutrition_mode: Mapped[NutritionMode | None] = mapped_column(
        SAEnum(NutritionMode, name="nutrition_mode", native_enum=True),
        nullable=True,
    )

    # Set when the user deletes their account (DELETE /v1/me). While non-null the
    # account is "being deleted": its access tokens are rejected. On deletion the
    # identity (email/apple_sub/google_sub) is detached so the user can sign in
    # again immediately and start a fresh account. A nightly purge hard-deletes
    # this row once it is older than the 7-day grace window (owned rows cascade
    # via the user_id FKs).
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

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
