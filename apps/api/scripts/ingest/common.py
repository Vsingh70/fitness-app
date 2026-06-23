"""Shared normalization + idempotent UPSERT for the food-data ingest scripts.

A ``NormalizedFood`` is the single shape both USDA and OFF ingest produce: a
source, an ``external_id`` (FDC id or barcode), a name, and per-100g macros. The
UPSERT is keyed on ``(source, external_id)`` against the partial unique index
``ix_foods_source_external`` so re-runs refresh rows instead of duplicating them.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FoodSource
from app.models.food import Food

UPSERT_BATCH_SIZE = 500

# foods.kcal_per_100g etc. are Numeric(7,2): max 99999.99. Clamp absurd source
# values (OFF has occasional bad rows) so a bad row can't abort the batch.
_MACRO_MAX = Decimal("99999.99")
# Numeric(8,2) for serving_size_g.
_SERVING_MAX = Decimal("999999.99")


@dataclass(frozen=True)
class NormalizedFood:
    """One food normalized to per-100g macros, ready to UPSERT into ``foods``."""

    source: FoodSource
    external_id: str
    name: str
    brand: str | None = None
    serving_size_g: Decimal | None = None
    serving_label: str | None = None
    kcal_per_100g: Decimal | None = None
    protein_g_per_100g: Decimal | None = None
    carbs_g_per_100g: Decimal | None = None
    fat_g_per_100g: Decimal | None = None
    fiber_g_per_100g: Decimal | None = None
    # Ingest-only metadata persisted to foods.payload (e.g. USDA category for
    # search ranking). Kept lean per the spec: only fields the app uses.
    payload: dict[str, Any] | None = None


def to_decimal(value: Any, *, cap: Decimal = _MACRO_MAX) -> Decimal | None:
    """Parse a macro value to a 2dp Decimal, clamped to the column's range.

    Returns None for missing/blank/unparseable values so a bad source row never
    aborts a batch. Negative values (junk) are dropped.
    """
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if parsed < 0:
        return None
    if parsed > cap:
        return cap
    return parsed


def serving_to_decimal(value: Any) -> Decimal | None:
    return to_decimal(value, cap=_SERVING_MAX)


def _row(food: NormalizedFood) -> dict[str, Any]:
    return {
        "source": food.source.value,
        "external_id": food.external_id,
        "name": food.name[:240],
        "brand": food.brand[:160] if food.brand else None,
        "serving_size_g": food.serving_size_g,
        "serving_label": food.serving_label,
        "kcal_per_100g": food.kcal_per_100g,
        "protein_g_per_100g": food.protein_g_per_100g,
        "carbs_g_per_100g": food.carbs_g_per_100g,
        "fat_g_per_100g": food.fat_g_per_100g,
        "fiber_g_per_100g": food.fiber_g_per_100g,
        "payload": food.payload or {},
    }


def batched(items: Iterable[NormalizedFood], size: int) -> Iterator[list[NormalizedFood]]:
    batch: list[NormalizedFood] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


async def upsert_foods(session: AsyncSession, foods: list[NormalizedFood]) -> int:
    """Idempotent UPSERT keyed on ``(source, external_id)``.

    Re-running refreshes macros/name/serving/payload in place rather than
    inserting duplicates (matches the ``ix_foods_source_external`` partial unique
    index where ``external_id IS NOT NULL``). Returns the number of rows written.

    Within a single batch the same ``(source, external_id)`` must not appear
    twice (Postgres rejects a second ON CONFLICT touch of the same row in one
    statement); the last occurrence wins after de-duplication here.
    """
    if not foods:
        return 0
    deduped: dict[tuple[str, str], NormalizedFood] = {}
    for food in foods:
        deduped[(food.source.value, food.external_id)] = food
    rows = [_row(f) for f in deduped.values()]

    insert = pg_insert(Food)
    stmt = insert.values(rows).on_conflict_do_update(
        index_elements=["source", "external_id"],
        index_where=Food.external_id.is_not(None),
        set_={
            "name": insert.excluded.name,
            "brand": insert.excluded.brand,
            "serving_size_g": insert.excluded.serving_size_g,
            "serving_label": insert.excluded.serving_label,
            "kcal_per_100g": insert.excluded.kcal_per_100g,
            "protein_g_per_100g": insert.excluded.protein_g_per_100g,
            "carbs_g_per_100g": insert.excluded.carbs_g_per_100g,
            "fat_g_per_100g": insert.excluded.fat_g_per_100g,
            "fiber_g_per_100g": insert.excluded.fiber_g_per_100g,
            "payload": insert.excluded.payload,
            "updated_at": datetime.now(tz=UTC),
        },
    )
    await session.execute(stmt)
    return len(rows)


async def upsert_stream(
    session: AsyncSession, foods: Iterable[NormalizedFood], *, batch_size: int = UPSERT_BATCH_SIZE
) -> int:
    """UPSERT a (possibly huge) stream of foods in batches, committing each.

    Streaming keeps memory flat for the multi-million-row OFF dump.
    """
    total = 0
    for batch in batched(foods, batch_size):
        total += await upsert_foods(session, batch)
        await session.commit()
    return total
