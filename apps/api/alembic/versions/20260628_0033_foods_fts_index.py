"""add full-text search index over foods name + brand

Food search now matches full-text tokens over ``name || ' ' || coalesce(brand,'')``
(``english`` config: stemming + stopword removal, so "chicken just bare" requires the
distinctive "bare" and excludes generic chicken) and orders by relevance first. This
adds a GIN index on that exact ``to_tsvector`` expression so the search filter uses an
index instead of scanning. The existing ``ix_foods_name_trgm`` trigram index stays (it
backs the fuzzy ``word_similarity`` fallback).

Revision ID: 0033_foods_fts_index
Revises: 0032_refresh_token_family_id
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033_foods_fts_index"
down_revision: str | None = "0032_refresh_token_family_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_foods_name_brand_fts ON foods "
        "USING gin (to_tsvector('english', name || ' ' || coalesce(brand, '')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_foods_name_brand_fts")
