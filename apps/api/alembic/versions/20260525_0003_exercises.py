"""exercises table with enums and trigram search

Revision ID: 0003_exercises
Revises: 0002_auth
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_exercises"
down_revision: str | None = "0002_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MUSCLES = [
    "chest",
    "lats",
    "traps",
    "rhomboids",
    "rear_delts",
    "side_delts",
    "front_delts",
    "biceps",
    "triceps",
    "forearms",
    "abs",
    "obliques",
    "lower_back",
    "glutes",
    "quads",
    "hamstrings",
    "adductors",
    "abductors",
    "calves",
]

EQUIPMENT = [
    "barbell",
    "dumbbell",
    "cable",
    "machine",
    "bodyweight",
    "banded",
    "kettlebell",
    "smith_machine",
    "trap_bar",
    "ez_bar",
    "plate_loaded",
    "cardio_machine",
    "other",
]

MOVEMENT_PATTERNS = [
    "squat",
    "hinge",
    "horizontal_push",
    "vertical_push",
    "horizontal_pull",
    "vertical_pull",
    "lunge",
    "carry",
    "rotation",
    "anti_rotation",
    "isolation",
    "cardio",
]

TRACKING_TYPES = [
    "weight_reps",
    "weight_reps_distance",
    "weight_time",
    "bodyweight_reps",
    "weighted_bodyweight",
    "time_only",
    "distance_time",
    "distance_time_pace",
    "cardio_machine",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    muscle_enum = postgresql.ENUM(*MUSCLES, name="muscle", create_type=True)
    equipment_enum = postgresql.ENUM(*EQUIPMENT, name="equipment", create_type=True)
    movement_pattern_enum = postgresql.ENUM(
        *MOVEMENT_PATTERNS, name="movement_pattern", create_type=True
    )
    tracking_type_enum = postgresql.ENUM(*TRACKING_TYPES, name="tracking_type", create_type=True)

    bind = op.get_bind()
    muscle_enum.create(bind, checkfirst=True)
    equipment_enum.create(bind, checkfirst=True)
    movement_pattern_enum.create(bind, checkfirst=True)
    tracking_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "exercises",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column(
            "primary_muscle",
            postgresql.ENUM(name="muscle", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "secondary_muscles",
            postgresql.ARRAY(postgresql.ENUM(name="muscle", create_type=False)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "equipment",
            postgresql.ENUM(name="equipment", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "movement_pattern",
            postgresql.ENUM(name="movement_pattern", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "tracking_type",
            postgresql.ENUM(name="tracking_type", create_type=False),
            nullable=False,
        ),
        sa.Column("is_unilateral", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cues", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_exercises_name", "exercises", ["name"])
    op.create_index("ix_exercises_owner_id", "exercises", ["owner_id"])
    op.create_index(
        "ix_exercises_name_trgm",
        "exercises",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_exercises_name_trgm", table_name="exercises")
    op.drop_index("ix_exercises_owner_id", table_name="exercises")
    op.drop_index("ix_exercises_name", table_name="exercises")
    op.drop_table("exercises")
    sa.Enum(name="tracking_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="movement_pattern").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="equipment").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="muscle").drop(op.get_bind(), checkfirst=True)
