from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base
from app.models.enums import NotificationKind


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[NotificationKind] = mapped_column(
        SAEnum(
            NotificationKind,
            name="notification_kind",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
