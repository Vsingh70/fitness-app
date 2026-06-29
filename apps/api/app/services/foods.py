"""Food lookup, search, and custom CRUD over the self-hosted ``foods`` table.

The app owns its food data in ``foods``: it can be bulk-ingested (USDA / Open Food
Facts scripts under ``scripts/``) and is also filled on demand — when a local
search is thin, ``search_foods`` fans out to the live USDA FoodData Central + Open
Food Facts search APIs, caches the hits, and re-ranks, so the catalogue grows with
use and repeat searches are local. The fallback is fail-open.

Search matches full-text tokens over ``name || ' ' || brand`` (``english`` config:
stemming + stopword removal, so "chicken just bare" requires the distinctive
"bare") OR a fuzzy trigram ``word_similarity`` for typos. Results are ordered by
match relevance FIRST, then a source-tier
tiebreak (lower sorts first): 0 custom, 1 USDA Foundation/SR Legacy, 2 USDA
Branded, 3 Open Food Facts, 4 anything else; then recency. Relevance-first means
a strong brand match wins regardless of source. Near-identical names are
de-duplicated so junk rows can't bury a clean hit.

Barcode:
- Resolve against local ``foods`` by ``external_id`` (USDA Branded GTINs and OFF
  barcodes are both stored there).
- On a miss, fall back to a live Open Food Facts lookup and cache the result into
  ``foods`` so the next scan is local.
"""

from __future__ import annotations

import asyncio
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
from app.clients import usda_fdc
from app.clients.remote_food import RemoteFood
from app.config import get_settings
from app.logging_config import get_logger
from app.models.enums import FoodSource
from app.models.food import Food
from app.models.user import User

log = get_logger("foods")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MIN_QUERY_LEN = 2
# Minimum trigram word-similarity for the fuzzy backstop when full-text doesn't
# match. Full-text (token AND-match) is the precise path; this catches typos of
# the whole query. Kept high so a single shared word in a multi-word query (e.g.
# "chicken" in "chicken just bare") doesn't flood results with loose matches.
MIN_WORD_SIMILARITY = Decimal("0.6")

# USDA payload categories that count as high-quality generic foods. Branded USDA
# rows carry "branded_food" (or no category) and sort below these.
USDA_GENERIC_CATEGORIES = ("foundation_food", "sr_legacy_food")

# Live-fallback tuning: when a local search yields fewer than this, fan out to the
# external search APIs, cache the hits, and re-rank.
MIN_LOCAL_RESULTS = 8
FALLBACK_FETCH_LIMIT = 25
# Must exceed the per-client search timeouts (OFF cgi search ~6s) so a slow but
# successful provider isn't cancelled by the overall gather budget.
FALLBACK_TIMEOUT_SECONDS = 8.0

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


async def _local_search(
    session: AsyncSession,
    user: User,
    *,
    q: str,
    source: FoodSource | None,
    min_protein_per_100g: Decimal | None,
    limit: int,
) -> list[Food]:
    """Relevance-ranked, de-duplicated search over the local ``foods`` table.

    Matches full-text tokens (``websearch_to_tsquery``, ``english`` config) over
    ``name || ' ' || brand``, OR a fuzzy trigram ``word_similarity`` for
    typos/partials. Orders by match relevance FIRST, then source tier (custom >
    USDA generic > USDA branded > OFF), then recency — so a strong brand match
    (e.g. "Just Bare" for "chicken just bare") wins regardless of source.
    """
    # Must match the expression index added in migration 0033.
    name_brand = Food.name.concat(" ").concat(func.coalesce(Food.brand, ""))
    tsv = func.to_tsvector("english", name_brand)
    tsq = func.websearch_to_tsquery("english", q)
    word_sim = func.word_similarity(q, name_brand)
    relevance = func.greatest(func.ts_rank(tsv, tsq), word_sim)
    rank = _rank_expression()

    stmt = (
        select(Food)
        .options(selectinload(Food.servings))
        .where(
            Food.archived_at.is_(None),
            # Only the user's own custom rows OR public rows.
            or_(Food.owner_id.is_(None), Food.owner_id == user.id),
            or_(tsv.op("@@")(tsq), word_sim >= float(MIN_WORD_SIMILARITY)),
        )
        .order_by(
            desc(relevance),
            asc(rank),
            desc(Food.created_at),
            desc(Food.id),
        )
        # Over-fetch so de-duplication still leaves a full page.
        .limit((limit + 1) * 3)
    )
    if source is not None:
        stmt = stmt.where(Food.source == source)
    if min_protein_per_100g is not None:
        stmt = stmt.where(Food.protein_g_per_100g >= min_protein_per_100g)

    ordered = (await session.execute(stmt)).scalars().all()

    # De-duplicate near-identical names: the first occurrence wins because the
    # query is already ranked best-match-first.
    seen: set[str] = set()
    rows: list[Food] = []
    for food in ordered:
        key = _dedupe_key(food.name)
        if key in seen:
            continue
        seen.add(key)
        rows.append(food)
        if len(rows) >= limit:
            break
    return rows


async def _live_fallback(q: str) -> list[RemoteFood]:
    """Fan out to the external search APIs (USDA FDC + Open Food Facts) for ``q``.

    Concurrent, time-boxed, and fail-open: any provider that errors or the whole
    batch timing out yields fewer (or no) results rather than failing the search.
    USDA is included only when an API key is configured.
    """
    settings = get_settings()
    tasks: list[Any] = [off.search_products(q, limit=FALLBACK_FETCH_LIMIT)]
    if settings.usda_fdc_api_key:
        tasks.append(
            usda_fdc.search(q, api_key=settings.usda_fdc_api_key, limit=FALLBACK_FETCH_LIMIT)
        )
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=FALLBACK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        log.warning("food_live_fallback_timeout", query=q)
        return []

    found: list[RemoteFood] = []
    for result in results:
        if isinstance(result, BaseException):
            log.warning("food_live_fallback_source_failed", error=repr(result))
            continue
        found.extend(result)
    return found


async def _cache_remote_foods(session: AsyncSession, foods: list[RemoteFood]) -> None:
    """Insert fetched foods into ``foods``, ignoring ones already cached.

    ``on_conflict_do_nothing`` on the ``(source, external_id)`` partial unique
    index makes this idempotent and race-safe (same pattern as barcode caching).
    """
    for food in foods:
        if not food.has_macros:
            continue
        stmt = (
            pg_insert(Food)
            .values(
                source=food.source,
                external_id=food.external_id,
                name=food.name,
                brand=food.brand,
                serving_size_g=food.serving_size_g,
                serving_label=food.serving_label,
                kcal_per_100g=food.kcal_per_100g,
                protein_g_per_100g=food.protein_g_per_100g,
                carbs_g_per_100g=food.carbs_g_per_100g,
                fat_g_per_100g=food.fat_g_per_100g,
                fiber_g_per_100g=food.fiber_g_per_100g,
                payload=food.payload,
            )
            .on_conflict_do_nothing(
                index_elements=["source", "external_id"],
                index_where=Food.external_id.is_not(None),
            )
        )
        await session.execute(stmt)
    await session.flush()


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
    """Relevance search over the catalogue, with a live fill-on-demand fallback.

    Searches the local ``foods`` table first (see ``_local_search``). When that's
    thin and no source filter is set, fans out to the live USDA FDC + Open Food
    Facts search APIs, caches the hits into ``foods``, and re-ranks — so the
    catalogue grows with real use and a repeat search is instant/local. The
    fallback is fail-open. Returns ``(rows, None)`` (a single ranked page).
    """
    if len(q.strip()) < MIN_QUERY_LEN:
        raise HTTPException(status_code=400, detail=f"`q` must be at least {MIN_QUERY_LEN} chars.")
    limit = max(1, min(limit, MAX_LIMIT))

    rows = await _local_search(
        session, user, q=q, source=source, min_protein_per_100g=min_protein_per_100g, limit=limit
    )

    if (
        get_settings().food_live_fallback_enabled
        and source is None
        and len(rows) < MIN_LOCAL_RESULTS
    ):
        fetched = await _live_fallback(q)
        if fetched:
            await _cache_remote_foods(session, fetched)
            log.info("food_live_fallback_cached", query=q, fetched=len(fetched))
            rows = await _local_search(
                session,
                user,
                q=q,
                source=source,
                min_protein_per_100g=min_protein_per_100g,
                limit=limit,
            )

    return rows, None


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
