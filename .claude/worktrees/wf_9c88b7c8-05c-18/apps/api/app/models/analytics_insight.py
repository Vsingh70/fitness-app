from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db import Base
from app.models.enums import AnalyticsInsightKind, AnalyticsInsightSeverity


class AnalyticsInsight(Base):
    __tablename__ = "analytics_insights"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    kind: Mapped[AnalyticsInsightKind] = mapped_column(
        SAEnum(
            AnalyticsInsightKind,
            name="analytics_insight_kind",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
    )
    severity: Mapped[AnalyticsInsightSeverity] = mapped_column(
        SAEnum(
            AnalyticsInsightSeverity,
            name="analytics_insight_severity",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    surfaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
