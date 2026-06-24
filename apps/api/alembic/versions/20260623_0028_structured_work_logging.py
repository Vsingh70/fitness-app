"""structured-work logging: set_segments, block kinds, intervals, rest default

Additive schema for the active-session logging redesign (``06-workout-session.md``
section 7 + ``05-active-session.md`` temp-swap). All changes are additive — a new
child table, nullable/defaulted columns, and enum extensions — so the existing test
suite stays green.

- new ``set_segments`` table: intra-set sub-bouts (rest-pause/cluster/myo as
  ``mini_set`` segments) and interval ``work``/``rest`` segments. ``kind`` is the new
  ``segment_kind`` enum (``work``/``rest``/``mini_set``).
- ``sets.rounds`` (nullable int) for interval round counts.
- ``workout_exercises.block_kind`` (new ``block_kind`` enum
  ``warmup``/``working``/``cooldown``, default ``working``) + nullable
  ``workout_exercises.block_label``.
- ``workout_exercises.substituted_for_exercise_id`` (nullable FK -> exercises) for a
  temporary one-session swap: the original pauses, logged sets credit the substitute.
- ``users.default_rest_seconds`` (int, default 90) preference.
- enum extensions: ``set_type`` gains ``interval``; ``movement_pattern`` gains
  ``mobility`` and ``plyometric`` so mobility/plyo movements are labeled and kept out
  of strength analytics.

Revision ID: 0028_structured_work_logging
Revises: 0027_flexible_microcycle_mesocycle
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028_structured_work_logging"
down_revision: str | None = "0027_flexible_microcycle_mesocycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- enum extensions (additive; ADD VALUE is idempotent on PG 12+ and safe in
    # this transaction since the new values aren't read in the same migration) ---
    op.execute("ALTER TYPE set_type ADD VALUE IF NOT EXISTS 'interval'")
    op.execute("ALTER TYPE movement_pattern ADD VALUE IF NOT EXISTS 'mobility'")
    op.execute("ALTER TYPE movement_pattern ADD VALUE IF NOT EXISTS 'plyometric'")

    # --- segment_kind enum + set_segments table ---
    segment_kind_enum = postgresql.ENUM(
        "work",
        "rest",
        "mini_set",
        name="segment_kind",
        create_type=True,
    )
    segment_kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "set_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(name="segment_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Numeric(8, 2), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["set_id"], ["sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "set_id",
            "segment_index",
            name="uq_set_segments_set_id_segment_index",
        ),
    )
    op.create_index("ix_set_segments_set_id", "set_segments", ["set_id"])

    # --- sets.rounds (interval round count) ---
    op.add_column("sets", sa.Column("rounds", sa.Integer(), nullable=True))

    # --- workout_exercises: block grouping + temp-swap link ---
    block_kind_enum = postgresql.ENUM(
        "warmup",
        "working",
        "cooldown",
        name="block_kind",
        create_type=True,
    )
    block_kind_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "workout_exercises",
        sa.Column(
            "block_kind",
            postgresql.ENUM(name="block_kind", create_type=False),
            nullable=False,
            server_default=sa.text("'working'"),
        ),
    )
    op.add_column(
        "workout_exercises",
        sa.Column("block_label", sa.String(80), nullable=True),
    )
    op.add_column(
        "workout_exercises",
        sa.Column(
            "substituted_for_exercise_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_workout_exercises_substituted_for_exercise_id_exercises",
        "workout_exercises",
        "exercises",
        ["substituted_for_exercise_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- users.default_rest_seconds preference (seeded at 90) ---
    op.add_column(
        "users",
        sa.Column(
            "default_rest_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("90"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "default_rest_seconds")

    op.drop_constraint(
        "fk_workout_exercises_substituted_for_exercise_id_exercises",
        "workout_exercises",
        type_="foreignkey",
    )
    op.drop_column("workout_exercises", "substituted_for_exercise_id")
    op.drop_column("workout_exercises", "block_label")
    op.drop_column("workout_exercises", "block_kind")
    op.execute("DROP TYPE block_kind")

    op.drop_column("sets", "rounds")

    op.drop_index("ix_set_segments_set_id", table_name="set_segments")
    op.drop_table("set_segments")
    op.execute("DROP TYPE segment_kind")

    # NOTE: Postgres has no DROP VALUE for enum types; the new 'interval' value on
    # set_type and 'mobility'/'plyometric' on movement_pattern stay on the type even
    # after downgrade. Acceptable for a single-dev project (mirrors 0012/0021).
