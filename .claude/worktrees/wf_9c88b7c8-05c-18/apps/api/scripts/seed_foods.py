"""Bulk-load USDA FoodData Central into the foods table.

The USDA download requires accepting their terms manually. Steps:

1. Visit https://fdc.nal.usda.gov/download-datasets.html
2. Download the latest "Foundation Foods" and "SR Legacy Foods" CSVs.
3. Optionally download a subset of "Branded Foods" (filter by date / brand).
4. Place the extracted CSVs in `apps/api/seed/usda/` with the canonical names:
   - food.csv          (id, name, food_category_id, data_type)
   - food_nutrient.csv (food_id, nutrient_id, amount per 100g)
   - nutrient.csv      (id, name, unit)

Then run from `apps/api`:

    uv run python -m scripts.seed_foods

The script is idempotent: it upserts on (source='usda', external_id=fdc_id).

Foundation + SR Legacy take ~1-2 minutes; the full Branded set takes much
longer and is intentionally skipped here. We rely on Open Food Facts (live)
for branded barcode lookups.
"""

from __future__ import annotations

import asyncio
import csv
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.models.enums import FoodSource
from app.models.food import Food

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "seed" / "usda"
DATA_TYPES = {"foundation_food", "sr_legacy_food"}

# Nutrient IDs from the USDA reference (`nutrient.csv`).
NUTRIENT_ENERGY_KCAL = 1008
NUTRIENT_PROTEIN_G = 1003
NUTRIENT_CARBS_G = 1005
NUTRIENT_FAT_G = 1004
NUTRIENT_FIBER_G = 1079


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return None


def _load_foods_csv() -> list[dict[str, Any]]:
    path = SEED_DIR / "food.csv"
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data_type = (row.get("data_type") or "").strip()
            if data_type not in DATA_TYPES:
                continue
            rows.append(
                {
                    "fdc_id": str(row["fdc_id"]),
                    "name": (row.get("description") or "").strip()[:240],
                    "category": data_type,
                }
            )
    return rows


def _load_nutrients_csv(fdc_ids: set[str]) -> dict[str, dict[int, Decimal | None]]:
    """Return {fdc_id: {nutrient_id: amount}} for the nutrients we care about."""
    wanted = {
        NUTRIENT_ENERGY_KCAL,
        NUTRIENT_PROTEIN_G,
        NUTRIENT_CARBS_G,
        NUTRIENT_FAT_G,
        NUTRIENT_FIBER_G,
    }
    path = SEED_DIR / "food_nutrient.csv"
    out: dict[str, dict[int, Decimal | None]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc_id = str(row["fdc_id"])
            if fdc_id not in fdc_ids:
                continue
            try:
                nutrient_id = int(row["nutrient_id"])
            except (TypeError, ValueError):
                continue
            if nutrient_id not in wanted:
                continue
            out.setdefault(fdc_id, {})[nutrient_id] = _to_decimal(row.get("amount"))
    return out


async def _upsert_batch(session: AsyncSession, batch: list[dict[str, Any]]) -> int:
    if not batch:
        return 0
    stmt = (
        pg_insert(Food)
        .values(batch)
        .on_conflict_do_update(
            index_elements=["source", "external_id"],
            set_={
                "name": pg_insert(Food).excluded.name,
                "kcal_per_100g": pg_insert(Food).excluded.kcal_per_100g,
                "protein_g_per_100g": pg_insert(Food).excluded.protein_g_per_100g,
                "carbs_g_per_100g": pg_insert(Food).excluded.carbs_g_per_100g,
                "fat_g_per_100g": pg_insert(Food).excluded.fat_g_per_100g,
                "fiber_g_per_100g": pg_insert(Food).excluded.fiber_g_per_100g,
                "payload": pg_insert(Food).excluded.payload,
            },
        )
    )
    await session.execute(stmt)
    return len(batch)


async def main() -> None:
    configure_logging()
    log = get_logger("seed_foods")
    if not SEED_DIR.exists():
        log.warning("usda_seed_dir_missing", path=str(SEED_DIR))
        return

    foods = _load_foods_csv()
    fdc_ids = {row["fdc_id"] for row in foods}
    log.info("usda_foods_loaded", count=len(foods))

    nutrients = _load_nutrients_csv(fdc_ids)
    log.info("usda_nutrients_loaded", rows=len(nutrients))

    sm = get_sessionmaker()
    async with sm() as session:
        batch: list[dict[str, Any]] = []
        for row in foods:
            n = nutrients.get(row["fdc_id"], {})
            batch.append(
                {
                    "source": FoodSource.usda.value,
                    "external_id": row["fdc_id"],
                    "name": row["name"],
                    "kcal_per_100g": n.get(NUTRIENT_ENERGY_KCAL),
                    "protein_g_per_100g": n.get(NUTRIENT_PROTEIN_G),
                    "carbs_g_per_100g": n.get(NUTRIENT_CARBS_G),
                    "fat_g_per_100g": n.get(NUTRIENT_FAT_G),
                    "fiber_g_per_100g": n.get(NUTRIENT_FIBER_G),
                    "payload": {"category": row["category"]},
                }
            )
            if len(batch) >= 500:
                await _upsert_batch(session, batch)
                batch = []
        if batch:
            await _upsert_batch(session, batch)
        await session.commit()
        log.info("usda_seed_done", inserted=len(foods))


if __name__ == "__main__":
    asyncio.run(main())
