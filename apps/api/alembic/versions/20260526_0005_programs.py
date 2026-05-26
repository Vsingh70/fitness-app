"""programs and program templates

Revision ID: 0005_programs
Revises: 0004_workouts
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_programs"
down_revision: str | None = "0004_workouts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROGRAM_GOAL = ["hypertrophy", "strength", "powerbuilding", "fat_loss", "general", "custom"]
PROGRAM_SOURCE = ["template", "manual", "copied"]
PROGRESSION_STRATEGY = ["linear", "double_progression", "rpe_based", "none"]


def upgrade() -> None:
    program_goal = postgresql.ENUM(*PROGRAM_GOAL, name="program_goal", create_type=True)
    program_source = postgresql.ENUM(*PROGRAM_SOURCE, name="program_source", create_type=True)
    progression_strategy = postgresql.ENUM(
        *PROGRESSION_STRATEGY, name="progression_strategy", create_type=True
    )
    bind = op.get_bind()
    program_goal.create(bind, checkfirst=True)
    program_source.create(bind, checkfirst=True)
    progression_strategy.create(bind, checkfirst=True)

    op.create_table(
        "program_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=160), nullable=True),
        sa.Column(
            "goal",
            postgresql.ENUM(name="program_goal", create_type=False),
            nullable=False,
        ),
        sa.Column("weeks", sa.Integer(), nullable=False),
        sa.Column("days_per_week", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "programs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "goal",
            postgresql.ENUM(name="program_goal", create_type=False),
            nullable=False,
        ),
        sa.Column("weeks", sa.Integer(), nullable=False),
        sa.Column("days_per_week", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            postgresql.ENUM(name="program_source", create_type=False),
            nullable=False,
        ),
        sa.Column("template_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["program_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_programs_owner_id", "programs", ["owner_id"])

    op.create_table(
        "program_days",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
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
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_program_days_program_id", "program_days", ["program_id"])

    op.create_table(
        "program_day_exercises",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_day_id", sa.UUID(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("target_sets", sa.Integer(), nullable=False),
        sa.Column("target_reps_low", sa.Integer(), nullable=True),
        sa.Column("target_reps_high", sa.Integer(), nullable=True),
        sa.Column("target_rpe_low", sa.Numeric(3, 1), nullable=True),
        sa.Column("target_rpe_high", sa.Numeric(3, 1), nullable=True),
        sa.Column("target_rir_low", sa.Integer(), nullable=True),
        sa.Column("target_rir_high", sa.Integer(), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "progression_strategy",
            postgresql.ENUM(name="progression_strategy", create_type=False),
            nullable=False,
            server_default="none",
        ),
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
        sa.ForeignKeyConstraint(["program_day_id"], ["program_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_program_day_exercises_day_id", "program_day_exercises", ["program_day_id"])


def downgrade() -> None:
    op.drop_index("ix_program_day_exercises_day_id", table_name="program_day_exercises")
    op.drop_table("program_day_exercises")
    op.drop_index("ix_program_days_program_id", table_name="program_days")
    op.drop_table("program_days")
    op.drop_index("ix_programs_owner_id", table_name="programs")
    op.drop_table("programs")
    op.drop_table("program_templates")
    bind = op.get_bind()
    sa.Enum(name="progression_strategy").drop(bind, checkfirst=True)
    sa.Enum(name="program_source").drop(bind, checkfirst=True)
    sa.Enum(name="program_goal").drop(bind, checkfirst=True)
