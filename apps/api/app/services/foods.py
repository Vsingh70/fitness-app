"""Food lookup, search, and custom CRUD over the self-hosted ``foods`` table.

The app owns its food data: USDA FoodData Central (Foundation, SR Legacy, Branded)
and Open Food Facts are bulk-ingested into ``foods`` by the scripts under
``scripts/`` and searched locally via the existing ``pg_trgm`` GIN index on
``name``. There is no live search provider; search is instant, offline-capable,
and rate-limit-free.

Search ranking (lower rank sorts first):
- 0  custom (the user's own entries)
- 1  USDA Foundation / SR Legacy (clean generic whole foods)
- 2  USDA Branded (US branded, GTIN/UPC)
- 3  Open Food Facts (global breadth, uneven quality)
- 4  anything else (e.g. legacy ``user``)
Within a rank, trigram similarity to the query DESC, then recency. Near-identical
names are de-duplicated so junk OFF rows can't bury a clean generic hit.

Barcode:
- Resolve against local ``foods`` by ``external_id`` (USDA Branded GTINs and OFF
  barcodes are both stored there).
- On a miss, fall back to a live Open Food Facts lookup and cache the result into
  ``foods`` so the next scan is local.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, asc, case, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients import openfoodfacts as off
from app.models.enums import FoodSource
from app.models.food import Food
from app.models.user import User
from app.services.pagination import decode_created_at_id_cursor, encode_created_at_id_cursor

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MIN_QUERY_LEN = 2
SIMILARITY_THRESHOLD = Decimal("0.2")

# USDA payload categories that count as high-quality generic foods. Branded USDA
# rows carry "branded_food" (or no category) and sort below these.
USDA_GENERIC_CATEGORIES = ("foundation_food", "sr_legacy_food")

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _rank_expression() -> Any:
    """Lower number sorts first.

    custom=0, USDA generic (Foundation/SR Legacy)=1, USDA branded=2, OFF=3,
    everything else (legacy ``user``)=4. USDA generic vs branded is decided by the
    ingested ``payload.category`` (Foundation/SR Legacy are generic).
    """
    usda_generic = and_(
        Food.source == FoodSource.usda,
        Food.payload["category"].astext.in_(USDA_GENERIC_CATEGORIES),
    )
    return case(
        (Food.source == FoodSource.custom, 0),
        (usda_generic, 1),
        (Food.source == FoodSource.usda, 2),
        (Food.source == FoodSource.off, 3),
        else_=4,
    )


def _dedupe_key(name: str) -> str:
    """Normalized name for de-duplicating near-identical search hits.

    Lowercase, strip non-alphanumerics, collapse whitespace. "Chicken Breast,
    Raw" and "chicken breast raw" collapse to the same key so the higher-ranked
    source wins and the duplicate is dropped.
    """
    collapsed = _NON_ALNUM.sub(" ", name.lower()).strip()
    return collapsed


async def search_foods(
    session: AsyncSession,
    user: User,
    *,
    q: str,
    source: FoodSource | None = None,
    min_protein_per_100g: Decimal | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Food], str | None]:
    """Trigram search over ``foods.name`` against the self-hosted catalogue.

    Returns ``(rows, next_cursor)``. Ranks custom > USDA generic > USDA branded >
    OFF and de-duplicates near-identical names. ``next_cursor`` is created_at + id
    (DESC) for stable pagination after the ranked first page.
    """
    if len(q.strip()) < MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"`q` must be at least {MIN_QUERY_LEN} chars.")
    limit = max(1, min(limit, MAX_LIMIT))

    similarity = func.similarity(Food.name, q)
    rank = _rank_expression()

    stmt = (
        select(Food, similarity.label("similarity"), rank.label("rank"))
        .options(selectinload(Food.servings))
        .where(
            Food.archived_at.is_(None),
            similarity >= float(SIMILARITY_THRESHOLD),
            # Only the user's own custom rows OR public rows.
            or_(Food.owner_id.is_(None), Food.owner_id == user.id),
        )
        .order_by(
            asc(rank),
            desc(similarity),
            desc(Food.created_at),
            desc(Food.id),
        )
        # Over-fetch so de-duplication still leaves a full page (and a +1 to
        # detect whether another page exists).
        .limit((limit + 1) * 3)
    )
    if source is not None:
        stmt = stmt.where(Food.source == source)
    if min_protein_per_100g is not None:
        stmt = stmt.where(Food.protein_g_per_100g >= min_protein_per_100g)

    decoded = decode_created_at_id_cursor(cursor)
    if decoded is not None:
        cur_created, cur_id = decoded
        stmt = stmt.where(
            or_(
                Food.created_at < cur_created,
                and_(Food.created_at == cur_created, Food.id < cur_id),
            )
        )

    raw = (await session.execute(stmt)).all()
    ordered: list[Food] = [r[0] for r in raw]

    # De-duplicate near-identical names: the first occurrence wins because the
    # query is already ranked best-source-first.
    seen: set[str] = set()
    rows: list[Food] = []
    for food in ordered:
        key = _dedupe_key(food.name)
        if key in seen:
            continue
        seen.add(key)
        rows.append(food)
        if len(rows) > limit:
            break

    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_created_at_id_cursor(last.created_at, last.id)
    return rows, next_cursor


# ---------------------------------------------------------------------------
# Detail by id
# ---------------------------------------------------------------------------


async def get_food_by_id(session: AsyncSession, user: User, food_id: UUID) -> Food:
    """Return a single food (with servings) the user may see: public or own."""
    record = (
        await session.execute(
            select(Food)
            .options(selectinload(Food.servings))
            .where(
                Food.id == food_id,
                Food.archived_at.is_(None),
                or_(Food.owner_id.is_(None), Food.owner_id == user.id),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="not_found")
    return record


# ---------------------------------------------------------------------------
# Barcode lookup
# ---------------------------------------------------------------------------

# Sources a barcode can resolve to locally, in rank order: a custom row the user
# scanned, a USDA Branded GTIN, then an OFF barcode.
_BARCODE_SOURCES = (FoodSource.custom, FoodSource.usda, FoodSource.off)


async def _existing_by_barcode(session: AsyncSession, barcode: str) -> Food | None:
    """Match a barcode against any cached source (custom > usda > off)."""
    rows = (
        await session.execute(
            select(Food)
            .options(selectinload(Food.servings))
            .where(
                Food.external_id == barcode,
                Food.archived_at.is_(None),
                Food.source.in_(_BARCODE_SOURCES),
            )
            .order_by(_rank_expression())
            .limit(1)
        )
    ).first()
    return rows[0] if rows else None


async def lookup_barcode(session: AsyncSession, barcode: str) -> Food:
    """Cached barcode lookup. Tries the local catalogue, then live OFF.

    Raises HTTPException(404, 'not_found') if both miss, 502 if the OFF fallback
    is unreachable.
    """
    cached = await _existing_by_barcode(session, barcode)
    if cached is not None:
        return cached

    try:
        product = await off.fetch_product(barcode)
    except off.OffNotFoundError as exc:
        raise HTTPException(status_code=404, detail="not_found") from exc
    except off.OffClientError as exc:
        raise HTTPException(status_code=502, detail="off_unreachable") from exc

    # Cache by inserting; tolerate races via on_conflict_do_nothing on the
    # partial unique index (which matches our `external_id IS NOT NULL` row).
    stmt = (
        pg_insert(Food)
        .values(
            source=FoodSource.off.value,
            external_id=product.barcode,
            name=product.name,
            brand=product.brand,
            serving_size_g=product.serving_size_g,
            serving_label=product.serving_label,
            kcal_per_100g=product.kcal_per_100g,
            protein_g_per_100g=product.protein_g_per_100g,
            carbs_g_per_100g=product.carbs_g_per_100g,
            fat_g_per_100g=product.fat_g_per_100g,
            fiber_g_per_100g=product.fiber_g_per_100g,
            payload={},
        )
        .on_conflict_do_nothing(
            index_elements=["source", "external_id"],
            index_where=Food.external_id.is_not(None),
        )
    )
    await session.execute(stmt)
    await session.flush()
    record = await _existing_by_barcode(session, barcode)
    if record is None:
        raise HTTPException(status_code=500, detail="cache_insert_failed")
    return record


# ---------------------------------------------------------------------------
# Custom CRUD
# ---------------------------------------------------------------------------


async def create_custom_food(session: AsyncSession, user: User, payload: dict[str, Any]) -> Food:
    record = Food(
        source=FoodSource.custom,
        external_id=payload.get("external_id"),
        name=payload["name"],
        brand=payload.get("brand"),
        serving_size_g=payload.get("serving_size_g"),
        serving_label=payload.get("serving_label"),
        kcal_per_100g=payload.get("kcal_per_100g"),
        protein_g_per_100g=payload.get("protein_g_per_100g"),
        carbs_g_per_100g=payload.get("carbs_g_per_100g"),
        fat_g_per_100g=payload.get("fat_g_per_100g"),
        fiber_g_per_100g=payload.get("fiber_g_per_100g"),
        owner_id=user.id,
        payload={},
    )
    # Initialize the collection so model_validate doesn't lazy-load it post-commit.
    # Custom foods carry no servings yet (user-defined servings are a later task).
    record.servings = []
    session.add(record)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="A custom food with that name already exists."
        ) from exc
    return record


async def _owned_food(session: AsyncSession, user: User, food_id: UUID) -> Food:
    record = (
        await session.execute(
            select(Food)
            .options(selectinload(Food.servings))
            .where(
                Food.id == food_id,
                Food.owner_id == user.id,
                Food.archived_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Food not found.")
    return record


async def update_custom_food(
    session: AsyncSession, user: User, food_id: UUID, updates: dict[str, Any]
) -> Food:
    record = await _owned_food(session, user, food_id)
    for field, value in updates.items():
        setattr(record, field, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="A custom food with that name already exists."
        ) from exc
    return record


async def delete_or_archive_custom_food(session: AsyncSession, user: User, food_id: UUID) -> bool:
    """Hard-delete if no meal_items reference this food yet; otherwise archive.

    Returns True if archived (kept), False if hard-deleted.
    """
    record = await _owned_food(session, user, food_id)

    table_exists = (
        await session.execute(select(func.to_regclass("public.meal_items")))
    ).scalar_one()
    if table_exists is not None:
        from sqlalchemy import text as _text

        referenced = (
            await session.execute(
                _text("SELECT 1 FROM meal_items WHERE food_id = :id LIMIT 1"),
                {"id": str(record.id)},
            )
        ).first()
        if referenced is not None:
            record.archived_at = _now()
            await session.flush()
            return True
    await session.delete(record)
    await session.flush()
    return False
