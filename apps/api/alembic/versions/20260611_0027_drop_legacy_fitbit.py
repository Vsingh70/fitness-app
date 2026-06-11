"""drop legacy direct-Fitbit integration

Phase 4 of the Fitbit -> Google Health migration: removes the legacy
direct-Fitbit integration. Drops the ``fitbit_activities`` table and the
push-to-fitbit columns on ``users`` and ``workout_sessions``.

The ``fitbit_connections`` table is intentionally KEPT: the Google Health
integration reuses it (provider-agnostic encrypted token storage).

Revision ID: 0027_drop_legacy_fitbit
Revises: 0026_program_intensity_rep_mode
Create Date: 2026-06-11

Re-chained onto 0026_program_intensity_rep_mode (the current head) so this
branch linearizes after the perf, nutrition, and programs migrations that
merged to main first.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027_drop_legacy_fitbit"
down_revision: str | None = "0026_program_intensity_rep_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_fitbit_activities_user_started", table_name="fitbit_activities")
    op.drop_index("ix_fitbit_activities_user_id", table_name="fitbit_activities")
    op.drop_table("fitbit_activities")

    op.drop_column("users", "auto_push_to_fitbit")
    op.drop_column("workout_sessions", "fitbit_pushed_at")
    op.drop_column("workout_sessions", "fitbit_log_id")


def downgrade() -> None:
    op.add_column(
        "workout_sessions",
        sa.Column("fitbit_log_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "workout_sessions",
        sa.Column("fitbit_pushed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "auto_push_to_fitbit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
