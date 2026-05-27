"""foods table with food_source enum, pg_trgm GIN, and partial unique constraints

Revision ID: 0013_foods
Revises: 0012_insights_v2
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_foods"
down_revision: str | None = "0012_insights_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FOOD_SOURCES = ("usda", "off", "custom", "user")


def upgrade() -> None:
    enum = postgresql.ENUM(*FOOD_SOURCES, name="food_source", create_type=True)
    enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "foods",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            postgresql.ENUM(name="food_source", create_type=False),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("brand", sa.String(160), nullable=True),
        sa.Column("serving_size_g", sa.Numeric(8, 2), nullable=True),
        sa.Column("serving_label", sa.Text(), nullable=True),
        sa.Column("kcal_per_100g", sa.Numeric(7, 2), nullable=True),
        sa.Column("protein_g_per_100g", sa.Numeric(7, 2), nullable=True),
        sa.Column("carbs_g_per_100g", sa.Numeric(7, 2), nullable=True),
        sa.Column("fat_g_per_100g", sa.Numeric(7, 2), nullable=True),
        sa.Column("fiber_g_per_100g", sa.Numeric(7, 2), nullable=True),
        sa.Column(
            "owner_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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

    op.create_index("ix_foods_owner_id", "foods", ["owner_id"], unique=False)
    op.create_index(
        "ix_foods_source_external",
        "foods",
        ["source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    # Per-owner name uniqueness for custom foods so users don't accidentally
    # duplicate their own entries.
    op.create_index(
        "ix_foods_owner_name",
        "foods",
        ["owner_id", "name"],
        unique=True,
        postgresql_where=sa.text("owner_id IS NOT NULL AND archived_at IS NULL"),
    )
    op.create_index(
        "ix_foods_name_trgm",
        "foods",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_foods_name_trgm", table_name="foods")
    op.drop_index("ix_foods_owner_name", table_name="foods")
    op.drop_index("ix_foods_source_external", table_name="foods")
    op.drop_index("ix_foods_owner_id", table_name="foods")
    op.drop_table("foods")
    sa.Enum(name="food_source").drop(op.get_bind(), checkfirst=True)
