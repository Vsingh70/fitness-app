"""drop unused meals.photo_url column

Revision ID: 0019_drop_meal_photo_url
Revises: 0018_fitbit_needs_reauth
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_drop_meal_photo_url"
down_revision: str | None = "0018_fitbit_needs_reauth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("meals", "photo_url")


def downgrade() -> None:
    op.add_column("meals", sa.Column("photo_url", sa.Text(), nullable=True))
