"""workout sessions, exercises, sets + supporting tables

Revision ID: 0004_workouts
Revises: 0003_exercises
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_workouts"
down_revision: str | None = "0003_exercises"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SET_TYPES = [
    "working",
    "warmup",
    "drop",
    "myo_rep",
    "cluster",
    "top_set",
    "back_off",
    "amrap",
]


def upgrade() -> None:
    set_type_enum = postgresql.ENUM(*SET_TYPES, name="set_type", create_type=True)
    set_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_workout_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("bodyweight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("perceived_exertion", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "perceived_exertion is null or (perceived_exertion between 1 and 10)",
            name="ck_workout_sessions_perceived_exertion_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Partial index: only non-deleted sessions, ordered for the default list query.
    op.execute(
        "CREATE INDEX ix_workout_sessions_user_started "
        "ON workout_sessions (user_id, started_at DESC) "
        "WHERE deleted_at IS NULL"
    )

    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workout_session_id", sa.UUID(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["workout_session_id"], ["workout_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workout_exercises_session_position",
        "workout_exercises",
        ["workout_session_id", "position"],
    )

    op.create_table(
        "sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workout_exercise_id", sa.UUID(), nullable=False),
        sa.Column("set_index", sa.Integer(), nullable=False),
        sa.Column(
            "set_type",
            postgresql.ENUM(name="set_type", create_type=False),
            nullable=False,
            server_default="working",
        ),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Numeric(8, 2), nullable=True),
        sa.Column("rpe", sa.Numeric(3, 1), nullable=True),
        sa.Column("rir", sa.Integer(), nullable=True),
        sa.Column("is_pr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["workout_exercise_id"], ["workout_exercises.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sets_exercise_index", "sets", ["workout_exercise_id", "set_index"])
    # Covering index for fast last-session lookups (progression task uses this).
    op.execute(
        "CREATE INDEX ix_sets_exercise_covering "
        "ON sets (workout_exercise_id) INCLUDE (weight_kg, reps, rpe)"
    )

    op.create_table(
        "exercise_progression",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("best_e1rm_kg", sa.Numeric(7, 2), nullable=True),
        sa.Column("best_reps_bodyweight", sa.Integer(), nullable=True),
        sa.Column("best_pace_seconds_per_km", sa.Numeric(7, 2), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "exercise_id", name="uq_progression_user_ex"),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", "route", name="uq_idempotency_user_key_route"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("exercise_progression")
    op.drop_index("ix_sets_exercise_covering", table_name="sets")
    op.drop_index("ix_sets_exercise_index", table_name="sets")
    op.drop_table("sets")
    op.drop_index("ix_workout_exercises_session_position", table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index("ix_workout_sessions_user_started", table_name="workout_sessions")
    op.drop_table("workout_sessions")
    sa.Enum(name="set_type").drop(op.get_bind(), checkfirst=True)
