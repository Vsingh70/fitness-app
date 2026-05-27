"""Food lookup, search, and custom CRUD.

Search ranking:
- Source priority tier (custom=0, usda=1, off=2, user=3) ASC
- Trigram similarity vs the query DESC

Barcode flow:
- Check our DB by (source='off', external_id=barcode) AND by (source='usda',
  external_id=barcode) AND by (source='custom', external_id=barcode) so a user
  can prefer a custom override.
- On miss, call the OFF client. Cache the result by inserting a row with
  source='off'.
- If OFF says not_found, raise HTTPException(404, "not_found").
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, asc, case, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import openfoodfacts as off
from app.models.enums import FoodSource
from app.models.food import Food
from app.models.user import User
from app.services.pagination import decode_created_at_id_cursor, encode_created_at_id_cursor

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MIN_QUERY_LEN = 2
SIMILARITY_THRESHOLD = Decimal("0.2")


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _source_priority_expression() -> Any:
    """Lower number sorts first: custom 0, usda 1, off 2, user 3."""
    return case(
        (Food.source == FoodSource.custom, 0),
        (Food.source == FoodSource.usda, 1),
        (Food.source == FoodSource.off, 2),
        else_=3,
    )


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
    """Trigram search over name.

    Returns (rows, next_cursor). Cursor is created_at + id (DESC) for stable
    pagination after the ranked first page.
    """
    if len(q.strip()) < MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"`q` must be at least {MIN_QUERY_LEN} chars.")
    limit = max(1, min(limit, MAX_LIMIT))

    similarity = func.similarity(Food.name, q)
    priority = _source_priority_expression()

    stmt = (
        select(Food, similarity.label("similarity"), priority.label("priority"))
        .where(
            Food.archived_at.is_(None),
            similarity >= float(SIMILARITY_THRESHOLD),
            # Only the user's own custom rows OR public rows.
            or_(Food.owner_id.is_(None), Food.owner_id == user.id),
        )
        .order_by(
            asc(priority),
            desc(similarity),
            desc(Food.created_at),
            desc(Food.id),
        )
        .limit(limit + 1)
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
    rows: list[Food] = [r[0] for r in raw]
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_created_at_id_cursor(last.created_at, last.id)
    return rows, next_cursor


# ---------------------------------------------------------------------------
# Barcode lookup
# ---------------------------------------------------------------------------


async def _existing_by_barcode(session: AsyncSession, barcode: str) -> Food | None:
    """Match a barcode against any cached source (custom > usda > off)."""
    rows = (
        await session.execute(
            select(Food)
            .where(
                Food.external_id == barcode,
                Food.archived_at.is_(None),
                Food.source.in_((FoodSource.custom, FoodSource.usda, FoodSource.off)),
            )
            .order_by(_source_priority_expression())
            .limit(1)
        )
    ).first()
    return rows[0] if rows else None


async def lookup_barcode(session: AsyncSession, barcode: str) -> Food:
    """Cached barcode lookup. Raises 404 with detail='not_found' if missing
    locally AND on OFF. Raises 502 if OFF is unreachable.
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
            select(Food).where(
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

    NOTE: meal_items doesn't exist until task 06.03. Until then we always
    hard-delete since nothing can reference a food. The reference check is
    written defensively against an `information_schema` lookup so it
    transparently begins archiving once the table exists.
    """
    record = await _owned_food(session, user, food_id)

    # meal_items doesn't exist yet (task 06.03). Probe pg_catalog so this
    # function starts archiving instead of hard-deleting once the table lands.
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
