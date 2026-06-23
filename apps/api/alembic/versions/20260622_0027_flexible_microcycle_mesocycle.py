"""flexible microcycle/mesocycle program model

Replaces the rigid ``days_per_week``/``weeks`` program model with a flexible
microcycle (an ordered list of training/rest slots of any length) repeated into
a mesocycle and advanced by pure rotation.

- ``programs``: add ``microcycle_length`` (backfilled from ``days_per_week``) and
  ``mesocycle_length_microcycles`` (backfilled from ``mesocycle_length_weeks``);
  drop ``days_per_week``, ``weeks``, ``mesocycle_length_weeks``.
- ``program_days``: rename ``day_index`` -> ``slot_index``; add ``is_rest_day``.
- ``program_templates``: add ``microcycle_length`` (backfilled from
  ``days_per_week``), ``mesocycle_length_microcycles`` (default 4), ``owner_id``
  (FK users, CASCADE, indexed) and ``visibility`` (``template_visibility`` enum,
  NULL = curated); drop ``days_per_week``, ``weeks``.
- ``scheduled_workouts``: add ``microcycle_number`` (backfilled from
  ``mesocycle_week``) and ``repetition``; make ``scheduled_for`` nullable; drop
  ``mesocycle_week``.
- new ``program_progress`` table holding per-user-per-program rotation position.

Revision ID: 0027_flexible_microcycle_mesocycle
Revises: 0026_program_intensity_rep_mode
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027_flexible_microcycle_mesocycle"
down_revision: str | None = "0026_program_intensity_rep_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ``0027_flexible_microcycle_mesocycle`` is 34 chars; alembic's default
    # ``alembic_version.version_num`` is ``varchar(32)``. Widen it so this (and
    # every later) revision id fits, on fresh and existing databases alike.
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(length=64),
        existing_type=sa.String(length=32),
    )

    template_visibility_enum = postgresql.ENUM(
        "private",
        "shared",
        name="template_visibility",
        create_type=True,
    )
    template_visibility_enum.create(op.get_bind(), checkfirst=True)

    # --- programs: add nullable, backfill, set non-null, drop old ---
    op.add_column(
        "programs",
        sa.Column("microcycle_length", sa.Integer(), nullable=True),
    )
    op.add_column(
        "programs",
        sa.Column("mesocycle_length_microcycles", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE programs SET microcycle_length = days_per_week")
    op.execute("UPDATE programs SET mesocycle_length_microcycles = mesocycle_length_weeks")
    op.alter_column(
        "programs",
        "microcycle_length",
        nullable=False,
        server_default=sa.text("0"),
    )
    op.alter_column(
        "programs",
        "mesocycle_length_microcycles",
        nullable=False,
        server_default=sa.text("4"),
    )
    op.drop_column("programs", "days_per_week")
    op.drop_column("programs", "weeks")
    op.drop_column("programs", "mesocycle_length_weeks")

    # --- program_days: rename day_index -> slot_index, add is_rest_day ---
    op.alter_column("program_days", "day_index", new_column_name="slot_index")
    op.add_column(
        "program_days",
        sa.Column(
            "is_rest_day",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # --- program_templates: reshape ---
    op.add_column(
        "program_templates",
        sa.Column("microcycle_length", sa.Integer(), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column("mesocycle_length_microcycles", sa.Integer(), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column(
            "visibility",
            postgresql.ENUM(name="template_visibility", create_type=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_program_templates_owner_id_users",
        "program_templates",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_program_templates_owner_id",
        "program_templates",
        ["owner_id"],
    )
    op.execute("UPDATE program_templates SET microcycle_length = days_per_week")
    op.execute("UPDATE program_templates SET mesocycle_length_microcycles = 4")
    op.alter_column(
        "program_templates",
        "microcycle_length",
        nullable=False,
        server_default=sa.text("0"),
    )
    op.alter_column(
        "program_templates",
        "mesocycle_length_microcycles",
        nullable=False,
        server_default=sa.text("4"),
    )
    op.drop_column("program_templates", "days_per_week")
    op.drop_column("program_templates", "weeks")

    # --- scheduled_workouts: loosen date, swap mesocycle_week ---
    op.add_column(
        "scheduled_workouts",
        sa.Column("microcycle_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scheduled_workouts",
        sa.Column("repetition", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE scheduled_workouts SET microcycle_number = mesocycle_week")
    op.alter_column("scheduled_workouts", "scheduled_for", nullable=True)
    op.drop_column("scheduled_workouts", "mesocycle_week")

    # --- program_progress: new table ---
    op.create_table(
        "program_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "current_slot_index",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "current_microcycle_number",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "current_repetition",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "in_deload",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "last_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "program_id",
            name="uq_program_progress_user_program",
        ),
    )
    op.create_index(
        "ix_program_progress_user_id",
        "program_progress",
        ["user_id"],
    )
    op.create_index(
        "ix_program_progress_program_id",
        "program_progress",
        ["program_id"],
    )


def downgrade() -> None:
    # --- program_progress: drop table + indexes ---
    op.drop_index("ix_program_progress_program_id", table_name="program_progress")
    op.drop_index("ix_program_progress_user_id", table_name="program_progress")
    op.drop_table("program_progress")

    # --- scheduled_workouts: restore mesocycle_week, re-tighten date ---
    op.add_column(
        "scheduled_workouts",
        sa.Column("mesocycle_week", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE scheduled_workouts SET mesocycle_week = microcycle_number")
    # ``scheduled_for`` was NOT NULL before this revision; backfill any rows that
    # were created with a null date while the column was loosened so the NOT NULL
    # constraint can be restored without dropping data.
    op.execute(
        "UPDATE scheduled_workouts SET scheduled_for = CURRENT_DATE WHERE scheduled_for IS NULL"
    )
    op.alter_column("scheduled_workouts", "scheduled_for", nullable=False)
    op.drop_column("scheduled_workouts", "repetition")
    op.drop_column("scheduled_workouts", "microcycle_number")

    # --- program_templates: restore weeks/days_per_week, drop new columns ---
    op.add_column(
        "program_templates",
        sa.Column("weeks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column("days_per_week", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE program_templates SET days_per_week = microcycle_length")
    op.execute("UPDATE program_templates SET weeks = mesocycle_length_microcycles")
    op.alter_column("program_templates", "weeks", nullable=False)
    op.alter_column("program_templates", "days_per_week", nullable=False)
    op.drop_index("ix_program_templates_owner_id", table_name="program_templates")
    op.drop_constraint(
        "fk_program_templates_owner_id_users",
        "program_templates",
        type_="foreignkey",
    )
    op.drop_column("program_templates", "visibility")
    op.drop_column("program_templates", "owner_id")
    op.drop_column("program_templates", "mesocycle_length_microcycles")
    op.drop_column("program_templates", "microcycle_length")

    # --- program_days: drop is_rest_day, rename slot_index -> day_index ---
    op.drop_column("program_days", "is_rest_day")
    op.alter_column("program_days", "slot_index", new_column_name="day_index")

    # --- programs: restore weeks/days_per_week/mesocycle_length_weeks ---
    op.add_column(
        "programs",
        sa.Column("mesocycle_length_weeks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "programs",
        sa.Column("weeks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "programs",
        sa.Column("days_per_week", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE programs SET days_per_week = microcycle_length")
    op.execute("UPDATE programs SET mesocycle_length_weeks = mesocycle_length_microcycles")
    # ``weeks`` has no flexible-model counterpart; default to the legacy value of 6.
    op.execute("UPDATE programs SET weeks = 6")
    op.alter_column("programs", "mesocycle_length_weeks", nullable=False)
    op.alter_column("programs", "weeks", nullable=False)
    op.alter_column("programs", "days_per_week", nullable=False)
    op.drop_column("programs", "mesocycle_length_microcycles")
    op.drop_column("programs", "microcycle_length")

    # --- drop the enum last, after all columns referencing it are gone ---
    op.execute("DROP TYPE template_visibility")

    # NB: ``alembic_version.version_num`` is intentionally left widened to
    # varchar(64). Narrowing it here would fail, because alembic only rewrites
    # the version row to the (shorter) ``0026...`` id *after* ``downgrade()``
    # returns -- inside this transaction the column still holds the 34-char
    # ``0027...`` id. The wider column is harmless and forward-compatible.
