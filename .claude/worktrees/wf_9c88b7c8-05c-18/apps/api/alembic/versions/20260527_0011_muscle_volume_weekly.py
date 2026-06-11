"""muscle_volume_weekly rollup table

Revision ID: 0011_muscle_volume_weekly
Revises: 0010_mesocycles
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_muscle_volume_weekly"
down_revision: str | None = "0010_mesocycles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "muscle_volume_weekly",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("iso_year", sa.SmallInteger(), nullable=False),
        sa.Column("iso_week", sa.SmallInteger(), nullable=False),
        sa.Column(
            "muscle",
            postgresql.ENUM(name="muscle", create_type=False),
            nullable=False,
        ),
        sa.Column("working_sets", sa.Numeric(7, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("tonnage_kg", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("average_rir", sa.Numeric(4, 2), nullable=True),
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
        sa.UniqueConstraint(
            "user_id", "iso_year", "iso_week", "muscle", name="uq_mvw_user_week_muscle"
        ),
    )
    op.create_index(
        "ix_mvw_user_week",
        "muscle_volume_weekly",
        ["user_id", "iso_year", "iso_week"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mvw_user_week", table_name="muscle_volume_weekly")
    op.drop_table("muscle_volume_weekly")
