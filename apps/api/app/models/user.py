from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum as SAEnum, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db import Base
from app.models.enums import SexAtBirth, UnitSystem


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
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/New_York", nullable=False
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

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
