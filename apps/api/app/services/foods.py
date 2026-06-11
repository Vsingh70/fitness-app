"""Food lookup, search, and custom CRUD.

Primary search source is the FatSecret Platform API (replacing the USDA seed);
custom foods and the ``foods`` cache table stay. FatSecret results are normalized
into ``foods`` + ``food_servings`` on first sight and served from the cache after.

Search ranking:
- Source priority tier (custom=0, usda=1, fatsecret=2, off=3, user=4) ASC
- Trigram similarity vs the query DESC

Search flow:
- Trigram-search the local cache first.
- If the local cache is thin (first page, no cursor, few hits), resolve the
  query through FatSecret (search → food.get.v4 for the top hits), cache each
  food + its servings, then re-run the local query so ranking/paging is uniform.
- FatSecret being unconfigured/unreachable degrades silently to local results.

Barcode flow:
- Check our DB by (source in custom/usda/fatsecret/off, external_id=barcode).
- On miss, try FatSecret (find_id_for_barcode → food.get.v4) and cache it.
- If FatSecret misses / barcode method is unavailable, fall back to OFF.
- If both miss, raise HTTPException(404, 'not_found').
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, asc, case, desc, func, or_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients import fatsecret as fs
from app.clients import openfoodfacts as off
from app.models.enums import FoodSource, ServingUnit
from app.models.food import Food, FoodServing
from app.models.user import User
from app.services.pagination import decode_created_at_id_cursor, encode_created_at_id_cursor

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MIN_QUERY_LEN = 2
SIMILARITY_THRESHOLD = Decimal("0.2")
# Below this many local hits on the first page we reach out to FatSecret.
FATSECRET_TOPUP_THRESHOLD = 5
# How many FatSecret search hits we resolve to full detail (each is a food.get).
FATSECRET_DETAIL_LIMIT = 10
# Per-detail-call timeout for the search top-up. Tighter than the client's 8s
# default so a slow FatSecret can never hang a user-facing search request.
FATSECRET_DETAIL_TIMEOUT_SECONDS = 3.0


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _source_priority_expression() -> Any:
    """Lower number sorts first: custom 0, usda 1, fatsecret 2, off 3, user 4."""
    return case(
        (Food.source == FoodSource.custom, 0),
        (Food.source == FoodSource.usda, 1),
        (Food.source == FoodSource.fatsecret, 2),
        (Food.source == FoodSource.off, 3),
        else_=4,
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

    # First page of a FatSecret-eligible query (no explicit source filter, no
    # cursor): if the local cache is thin, resolve + cache fresh results so the
    # ranked query below serves a fuller catalogue. Misses degrade silently.
    if cursor is None and source in (None, FoodSource.fatsecret):
        await _maybe_topup_from_fatsecret(session, q)

    similarity = func.similarity(Food.name, q)
    priority = _source_priority_expression()

    stmt = (
        select(Food, similarity.label("similarity"), priority.label("priority"))
        .options(selectinload(Food.servings))
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
# FatSecret caching
# ---------------------------------------------------------------------------


def _serving_unit(raw: str | None) -> ServingUnit | None:
    if raw == "g":
        return ServingUnit.g
    if raw == "ml":
        return ServingUnit.ml
    return None


async def _replace_servings(
    session: AsyncSession, food_id: UUID, servings: list[fs.FatSecretServing]
) -> None:
    """Persist the full serving set for a food (replace any existing rows).

    Guarantees at least one default. If FatSecret marks none default, the first
    serving with a resolved gram weight becomes the default so meal entry always
    has a gram-convertible option.
    """
    await session.execute(sa_delete(FoodServing).where(FoodServing.food_id == food_id))
    if not servings:
        return
    has_default = any(s.is_default for s in servings)
    default_assigned = False
    for s in servings:
        is_default = s.is_default
        if not has_default and not default_assigned and s.grams is not None:
            is_default = True
            default_assigned = True
        session.add(
            FoodServing(
                food_id=food_id,
                description=s.description,
                metric_amount=s.metric_amount,
                metric_unit=_serving_unit(s.metric_unit),
                grams=s.grams,
                is_default=is_default,
            )
        )


async def _cache_fatsecret_food(session: AsyncSession, food: fs.FatSecretFood) -> Food:
    """Upsert a FatSecret food + its servings. Returns the persisted row.

    Idempotent on (source='fatsecret', external_id=food_id): a re-fetch refreshes
    the macros and replaces the serving set.
    """
    default_serving = next((s for s in food.servings if s.is_default), None)
    if default_serving is None:
        default_serving = next((s for s in food.servings if s.grams is not None), None)
    serving_size_g = default_serving.grams if default_serving else None
    serving_label = default_serving.description if default_serving else None

    values: dict[str, Any] = {
        "source": FoodSource.fatsecret.value,
        "external_id": food.food_id,
        "name": food.name,
        "brand": food.brand,
        "serving_size_g": serving_size_g,
        "serving_label": serving_label,
        "kcal_per_100g": food.kcal_per_100g,
        "protein_g_per_100g": food.protein_g_per_100g,
        "carbs_g_per_100g": food.carbs_g_per_100g,
        "fat_g_per_100g": food.fat_g_per_100g,
        "fiber_g_per_100g": food.fiber_g_per_100g,
        "payload": {},
    }
    stmt = (
        pg_insert(Food)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["source", "external_id"],
            index_where=Food.external_id.is_not(None),
            set_={
                "name": food.name,
                "brand": food.brand,
                "serving_size_g": serving_size_g,
                "serving_label": serving_label,
                "kcal_per_100g": food.kcal_per_100g,
                "protein_g_per_100g": food.protein_g_per_100g,
                "carbs_g_per_100g": food.carbs_g_per_100g,
                "fat_g_per_100g": food.fat_g_per_100g,
                "fiber_g_per_100g": food.fiber_g_per_100g,
                "updated_at": _now(),
            },
        )
    )
    await session.execute(stmt)
    record = (
        await session.execute(
            select(Food).where(
                Food.source == FoodSource.fatsecret,
                Food.external_id == food.food_id,
            )
        )
    ).scalar_one()
    await _replace_servings(session, record.id, food.servings)
    await session.flush()
    # The record was loaded (with an empty selectin servings collection) before
    # we inserted servings; reload so the response carries them.
    await session.refresh(record, ["servings"])
    return record


async def _maybe_topup_from_fatsecret(session: AsyncSession, query: str) -> None:
    """If the local cache is thin for ``query``, resolve + cache from FatSecret.

    Best-effort: an unconfigured or unreachable FatSecret is logged and ignored
    so search keeps serving the local cache. Caches each chosen hit's full detail
    (including servings) via food.get.v4.
    """
    local_hits = (
        await session.execute(
            select(func.count())
            .select_from(Food)
            .where(
                Food.archived_at.is_(None),
                func.similarity(Food.name, query) >= float(SIMILARITY_THRESHOLD),
                Food.source == FoodSource.fatsecret,
            )
        )
    ).scalar_one()
    if local_hits >= FATSECRET_TOPUP_THRESHOLD:
        return

    try:
        hits = await fs.search_foods(query, max_results=FATSECRET_DETAIL_LIMIT)
    except fs.FatSecretConfigError:
        return
    except (fs.FatSecretClientError, fs.FatSecretAuthError) as exc:
        logger.warning("fatsecret_search_unavailable", extra={"error": repr(exc)})
        return

    # Detail fetches are independent network calls: run them concurrently with
    # a tight per-call timeout. A failed/slow fetch skips that hit, as before.
    details = await asyncio.gather(
        *(_fetch_detail_for_topup(hit) for hit in hits), return_exceptions=True
    )
    # DB writes stay sequential: they all share this one AsyncSession.
    for detail in details:
        if isinstance(detail, BaseException):
            # Expected fetch errors are handled (and logged) inside
            # _fetch_detail_for_topup; anything surfacing here is unexpected.
            logger.warning("fatsecret_topup_unexpected_error", extra={"error": repr(detail)})
            continue
        if isinstance(detail, fs.FatSecretFood):
            await _cache_fatsecret_food(session, detail)
    await session.commit()


async def _fetch_detail_for_topup(hit: fs.FatSecretSearchHit) -> fs.FatSecretFood | None:
    """Fetch one search hit's full detail, best-effort. None on any miss/error."""
    try:
        async with asyncio.timeout(FATSECRET_DETAIL_TIMEOUT_SECONDS):
            return await fs.get_food(hit.food_id)
    except fs.FatSecretNotFoundError:
        return None
    except (fs.FatSecretClientError, fs.FatSecretAuthError, TimeoutError) as exc:
        logger.warning(
            "fatsecret_detail_unavailable",
            extra={"food_id": hit.food_id, "error": repr(exc)},
        )
        return None


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


async def _existing_by_barcode(session: AsyncSession, barcode: str) -> Food | None:
    """Match a barcode against any cached source (custom > usda > fatsecret > off)."""
    rows = (
        await session.execute(
            select(Food)
            .options(selectinload(Food.servings))
            .where(
                Food.external_id == barcode,
                Food.archived_at.is_(None),
                Food.source.in_(
                    (
                        FoodSource.custom,
                        FoodSource.usda,
                        FoodSource.fatsecret,
                        FoodSource.off,
                    )
                ),
            )
            .order_by(_source_priority_expression())
            .limit(1)
        )
    ).first()
    return rows[0] if rows else None


async def _fatsecret_barcode(session: AsyncSession, barcode: str) -> Food | None:
    """Resolve a barcode through FatSecret and cache it. None on miss / when the
    barcode method is unavailable / FatSecret is unconfigured, so the caller can
    fall through to OFF.
    """
    try:
        detail = await fs.lookup_barcode(barcode)
    except (fs.FatSecretNotFoundError, fs.FatSecretMethodNotAllowedError, fs.FatSecretConfigError):
        return None
    except (fs.FatSecretClientError, fs.FatSecretAuthError) as exc:
        logger.warning(
            "fatsecret_barcode_unavailable",
            extra={"barcode": barcode, "error": repr(exc)},
        )
        return None
    record = await _cache_fatsecret_food(session, detail)
    # FatSecret keys foods by its own id; also stash the scanned barcode so a
    # repeat scan hits the cache by external_id without another round-trip.
    if record.payload.get("barcode") != barcode:
        record.payload = {**record.payload, "barcode": barcode}
        await session.flush()
    return record


async def lookup_barcode(session: AsyncSession, barcode: str) -> Food:
    """Cached barcode lookup. Tries the local cache, then FatSecret, then OFF.

    Raises HTTPException(404, 'not_found') if all miss, 502 if OFF is the last
    resort and is unreachable.
    """
    cached = await _existing_by_barcode(session, barcode)
    if cached is not None:
        return cached

    by_barcode_payload = (
        await session.execute(
            select(Food)
            .options(selectinload(Food.servings))
            .where(
                Food.source == FoodSource.fatsecret,
                Food.archived_at.is_(None),
                Food.payload["barcode"].astext == barcode,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if by_barcode_payload is not None:
        return by_barcode_payload

    fatsecret_hit = await _fatsecret_barcode(session, barcode)
    if fatsecret_hit is not None:
        return fatsecret_hit

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
