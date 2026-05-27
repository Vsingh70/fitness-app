"""recommendations + progression rolling state

Revision ID: 0008_recommendations
Revises: 0007_notifications
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_recommendations"
down_revision: str | None = "0007_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = [
    "increase_weight",
    "increase_reps",
    "hold",
    "deload",
    "swap",
    "add_set",
    "remove_set",
]


def upgrade() -> None:
    enum = postgresql.ENUM(*KINDS, name="recommendation_kind", create_type=True)
    enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_workout_id", sa.UUID(), nullable=True),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(name="recommendation_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("rationale_key", sa.Text(), nullable=True),
        sa.Column("suggested_weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("suggested_reps_low", sa.Integer(), nullable=True),
        sa.Column("suggested_reps_high", sa.Integer(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["scheduled_workout_id"], ["scheduled_workouts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.execute(
        "CREATE UNIQUE INDEX ix_recommendations_active "
        "ON recommendations (user_id, scheduled_workout_id, exercise_id) "
        "WHERE consumed_at IS NULL AND dismissed_at IS NULL"
    )

    op.add_column(
        "exercise_progression",
        sa.Column("current_top_set_weight_kg", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "exercise_progression",
        sa.Column("current_target_reps_low", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exercise_progression",
        sa.Column("current_target_reps_high", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exercise_progression",
        sa.Column(
            "consecutive_successes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "exercise_progression",
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("exercise_progression", "consecutive_failures")
    op.drop_column("exercise_progression", "consecutive_successes")
    op.drop_column("exercise_progression", "current_target_reps_high")
    op.drop_column("exercise_progression", "current_target_reps_low")
    op.drop_column("exercise_progression", "current_top_set_weight_kg")
    op.execute("DROP INDEX IF EXISTS ix_recommendations_active")
    op.drop_index("ix_recommendations_user_id", table_name="recommendations")
    op.drop_table("recommendations")
    sa.Enum(name="recommendation_kind").drop(op.get_bind(), checkfirst=True)
