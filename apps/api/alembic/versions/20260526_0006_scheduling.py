"""scheduled_workouts + programs.is_active

Revision ID: 0006_scheduling
Revises: 0005_programs
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_scheduling"
down_revision: str | None = "0005_programs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ["planned", "in_progress", "completed", "skipped"]


def upgrade() -> None:
    enum = postgresql.ENUM(*STATUSES, name="scheduled_workout_status", create_type=True)
    enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "programs",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "programs",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    # At most one active, non-deleted program per user.
    op.execute(
        "CREATE UNIQUE INDEX ix_programs_one_active_per_user "
        "ON programs (owner_id) WHERE is_active AND deleted_at IS NULL"
    )

    op.create_table(
        "scheduled_workouts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=True),
        sa.Column("program_day_id", sa.UUID(), nullable=True),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="scheduled_workout_status", create_type=False),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("mesocycle_week", sa.Integer(), nullable=True),
        sa.Column("is_deload", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_day_id"], ["program_days.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scheduled_workouts_user_date",
        "scheduled_workouts",
        ["user_id", "scheduled_for"],
    )

    # Wire workout_sessions.scheduled_workout_id (column already exists) to the new table.
    op.create_foreign_key(
        "fk_workout_sessions_scheduled",
        "workout_sessions",
        "scheduled_workouts",
        ["scheduled_workout_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_workout_sessions_scheduled", "workout_sessions", type_="foreignkey")
    op.drop_index("ix_scheduled_workouts_user_date", table_name="scheduled_workouts")
    op.drop_table("scheduled_workouts")
    op.execute("DROP INDEX IF EXISTS ix_programs_one_active_per_user")
    op.drop_column("programs", "activated_at")
    op.drop_column("programs", "is_active")
    sa.Enum(name="scheduled_workout_status").drop(op.get_bind(), checkfirst=True)
