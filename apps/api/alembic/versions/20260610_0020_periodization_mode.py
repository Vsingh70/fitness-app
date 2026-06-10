"""periodization mode (block vs continuous) + reactive-deload flag

Revision ID: 0020_periodization_mode
Revises: 0019_drop_meal_photo_url
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020_periodization_mode"
down_revision: str | None = "0019_drop_meal_photo_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    periodization_enum = postgresql.ENUM(
        "block",
        "continuous",
        name="periodization_mode",
        create_type=True,
    )
    periodization_enum.create(op.get_bind(), checkfirst=True)

    # Existing rows backfill to 'block' via the server_default, preserving the
    # current finite-mesocycle behavior.
    op.add_column(
        "programs",
        sa.Column(
            "periodization_mode",
            postgresql.ENUM(name="periodization_mode", create_type=False),
            nullable=False,
            server_default=sa.text("'block'::periodization_mode"),
        ),
    )
    op.add_column(
        "programs",
        sa.Column(
            "auto_deload_on_stall",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("programs", "auto_deload_on_stall")
    op.drop_column("programs", "periodization_mode")
    op.execute("DROP TYPE periodization_mode")
