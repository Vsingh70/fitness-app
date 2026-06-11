"""fitbit_connections, fitbit_activities, daily_metrics

Revision ID: 0015_fitbit
Revises: 0014_meals
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_fitbit"
down_revision: str | None = "0014_meals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fitbit_connections",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("fitbit_user_id", sa.String(64), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column("last_synced_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "fitbit_activities",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("fitbit_log_id", sa.BigInteger(), nullable=False),
        sa.Column("activity_type", sa.String(120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("average_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "raw",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "fitbit_log_id", name="uq_fitbit_activities_user_log"),
    )
    op.create_index(
        "ix_fitbit_activities_user_started",
        "fitbit_activities",
        ["user_id", "started_at"],
        unique=False,
    )

    op.create_table(
        "daily_metrics",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("resting_hr", sa.Integer(), nullable=True),
        sa.Column("hrv_ms", sa.Numeric(6, 2), nullable=True),
        sa.Column("sleep_minutes", sa.Integer(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),
    )
    op.create_index(
        "ix_daily_metrics_user_date",
        "daily_metrics",
        ["user_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_metrics_user_date", table_name="daily_metrics")
    op.drop_table("daily_metrics")
    op.drop_index("ix_fitbit_activities_user_started", table_name="fitbit_activities")
    op.drop_table("fitbit_activities")
    op.drop_table("fitbit_connections")
