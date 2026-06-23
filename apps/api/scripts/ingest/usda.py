"""USDA FoodData Central (FDC) bulk ingest: Foundation, SR Legacy, Branded.

FDC publishes per-data-type CSV bundles (and an "all foods" bundle) at
https://fdc.nal.usda.gov/download-datasets.html . Each bundle extracts to a set
of CSVs; we read three:

- ``food.csv``           — ``fdc_id``, ``data_type``, ``description``
- ``food_nutrient.csv``  — ``fdc_id``, ``nutrient_id``, ``amount`` (per 100 g)
- ``branded_food.csv``   — (Branded only) ``fdc_id``, ``brand_owner``, ``gtin_upc``,
                            ``serving_size``, ``serving_size_unit``

FDC nutrient amounts in ``food_nutrient.csv`` are already per 100 g for these
data types, so normalization is a straight column map (no serving math). We
ingest the macros the app uses and tag each row's ``data_type`` into
``foods.payload.category`` so search can rank Foundation/SR Legacy above Branded.

UPSERT key: ``source='usda'``, ``external_id`` = FDC id. Branded rows ALSO get a
second OFF-style row keyed by GTIN/UPC so a barcode scan resolves a USDA branded
product locally — see ``branded_barcode_rows``.

Network/disk: ``download_fdc_bundle`` is the only heavy step and is intentionally
kept out of the test path. Tests drive ``parse_*`` + the UPSERT with small inline
CSV fixtures.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import zipfile
from collections.abc import Iterable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import TextIO

import httpx

from app.db import dispose_engine, get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.models.enums import FoodSource

from .common import NormalizedFood, serving_to_decimal, to_decimal, upsert_stream

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "seed" / "usda"

# data_type values we ingest. Foundation + SR Legacy are clean generic foods;
# Branded is US branded products (GTIN/UPC for barcode coverage).
GENERIC_DATA_TYPES = frozenset({"foundation_food", "sr_legacy_food"})
BRANDED_DATA_TYPE = "branded_food"
INGESTED_DATA_TYPES = GENERIC_DATA_TYPES | {BRANDED_DATA_TYPE}

# Nutrient IDs from the FDC ``nutrient.csv`` reference (per 100 g).
NUTRIENT_ENERGY_KCAL = 1008
NUTRIENT_PROTEIN_G = 1003
NUTRIENT_CARBS_G = 1005
NUTRIENT_FAT_G = 1004
NUTRIENT_FIBER_G = 1079
WANTED_NUTRIENTS = frozenset(
    {
        NUTRIENT_ENERGY_KCAL,
        NUTRIENT_PROTEIN_G,
        NUTRIENT_CARBS_G,
        NUTRIENT_FAT_G,
        NUTRIENT_FIBER_G,
    }
)

# FDC bulk download bundles (per data type). These are stable public URLs; the
# date suffix changes per release, so prefer the "latest" landing page in the
# runbook and pass an explicit URL/path when automating.
FDC_BUNDLE_URLS = {
    "foundation": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv.zip",
    "sr_legacy": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv.zip",
    "branded": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv.zip",
}


# ---------------------------------------------------------------------------
# Download (heavy; not exercised by tests)
# ---------------------------------------------------------------------------


def download_fdc_bundle(bundle: str, dest_dir: Path, *, timeout: float = 600.0) -> Path:
    """Download + extract one FDC CSV bundle into ``dest_dir``.

    ``bundle`` is one of ``FDC_BUNDLE_URLS``. Returns the directory the CSVs were
    extracted to. This is the only multi-GB step; the runbook runs it on the VPS.
    Kept out of the test path — tests use inline CSV fixtures instead.
    """
    url = FDC_BUNDLE_URLS[bundle]
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"{bundle}.zip"
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with zip_path.open("wb") as fh:
            for chunk in response.iter_bytes(chunk_size=1 << 20):
                fh.write(chunk)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink(missing_ok=True)
    return dest_dir


# ---------------------------------------------------------------------------
# Parse (pure; tested)
# ---------------------------------------------------------------------------


def parse_nutrients(food_nutrient_csv: TextIO) -> dict[str, dict[int, Decimal | None]]:
    """Read ``food_nutrient.csv`` into ``{fdc_id: {nutrient_id: amount_per_100g}}``.

    Only the macros in ``WANTED_NUTRIENTS`` are retained.
    """
    out: dict[str, dict[int, Decimal | None]] = {}
    reader = csv.DictReader(food_nutrient_csv)
    for row in reader:
        fdc_id = (row.get("fdc_id") or "").strip()
        if not fdc_id:
            continue
        try:
            nutrient_id = int(row["nutrient_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if nutrient_id not in WANTED_NUTRIENTS:
            continue
        out.setdefault(fdc_id, {})[nutrient_id] = to_decimal(row.get("amount"))
    return out


def parse_branded(branded_food_csv: TextIO) -> dict[str, dict[str, str]]:
    """Read ``branded_food.csv`` into ``{fdc_id: {brand, gtin_upc, serving...}}``."""
    out: dict[str, dict[str, str]] = {}
    reader = csv.DictReader(branded_food_csv)
    for row in reader:
        fdc_id = (row.get("fdc_id") or "").strip()
        if not fdc_id:
            continue
        out[fdc_id] = {
            "brand": (row.get("brand_owner") or row.get("brand_name") or "").strip(),
            "gtin_upc": (row.get("gtin_upc") or "").strip(),
            "serving_size": (row.get("serving_size") or "").strip(),
            "serving_size_unit": (row.get("serving_size_unit") or "").strip().lower(),
        }
    return out


def _branded_serving_g(meta: dict[str, str]) -> Decimal | None:
    """Resolve a branded product's serving to grams (g or ml ≈ 1 g/ml)."""
    unit = meta.get("serving_size_unit") or ""
    if unit not in ("g", "ml"):
        return None
    return serving_to_decimal(meta.get("serving_size"))


def normalize_foods(
    food_csv: TextIO,
    nutrients: dict[str, dict[int, Decimal | None]],
    branded: dict[str, dict[str, str]] | None = None,
) -> Iterator[NormalizedFood]:
    """Yield one ``NormalizedFood`` per ingestible row in ``food.csv``.

    ``data_type`` is tagged into ``payload.category`` so search can rank
    Foundation/SR Legacy above Branded. Branded rows carry brand + serving.
    """
    branded = branded or {}
    reader = csv.DictReader(food_csv)
    for row in reader:
        data_type = (row.get("data_type") or "").strip()
        if data_type not in INGESTED_DATA_TYPES:
            continue
        fdc_id = (row.get("fdc_id") or "").strip()
        name = (row.get("description") or "").strip()
        if not fdc_id or not name:
            continue
        macros = nutrients.get(fdc_id, {})
        meta = branded.get(fdc_id, {})
        brand = meta.get("brand") or None
        gtin = meta.get("gtin_upc") or None
        payload: dict[str, str] = {"category": data_type}
        if gtin:
            # Lets a barcode scan map this GTIN back to the FDC row's payload.
            payload["gtin_upc"] = gtin
        yield NormalizedFood(
            source=FoodSource.usda,
            external_id=fdc_id,
            name=name,
            brand=brand,
            serving_size_g=_branded_serving_g(meta) if meta else None,
            payload=payload,
            kcal_per_100g=macros.get(NUTRIENT_ENERGY_KCAL),
            protein_g_per_100g=macros.get(NUTRIENT_PROTEIN_G),
            carbs_g_per_100g=macros.get(NUTRIENT_CARBS_G),
            fat_g_per_100g=macros.get(NUTRIENT_FAT_G),
            fiber_g_per_100g=macros.get(NUTRIENT_FIBER_G),
        )


def branded_barcode_rows(foods: Iterable[NormalizedFood]) -> Iterator[NormalizedFood]:
    """Project USDA Branded rows that carry a GTIN into barcode-keyed rows.

    A barcode scan resolves ``foods.external_id == <barcode>``. USDA's primary
    key is the FDC id, so we emit a second ``source='usda'`` row keyed by GTIN so
    branded scans hit the clean USDA data before falling back to OFF. Idempotent:
    the UPSERT key is ``(usda, gtin)``.
    """
    for food in foods:
        gtin = (food.payload or {}).get("gtin_upc")
        if not gtin:
            continue
        payload = {**(food.payload or {}), "fdc_id": food.external_id}
        yield NormalizedFood(
            source=FoodSource.usda,
            external_id=gtin,
            name=food.name,
            brand=food.brand,
            serving_size_g=food.serving_size_g,
            serving_label=food.serving_label,
            kcal_per_100g=food.kcal_per_100g,
            protein_g_per_100g=food.protein_g_per_100g,
            carbs_g_per_100g=food.carbs_g_per_100g,
            fat_g_per_100g=food.fat_g_per_100g,
            fiber_g_per_100g=food.fiber_g_per_100g,
            payload=payload,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _open(path: Path) -> TextIO:
    return path.open(newline="", encoding="utf-8-sig")


def load_normalized(data_dir: Path) -> list[NormalizedFood] | None:
    """Read + normalize the USDA CSVs in ``data_dir`` (blocking disk + CPU work).

    Returns the normalized food list, or None if the required CSVs are missing.
    Kept synchronous so the async runner can offload it to a thread (large CSVs
    must not parse on the event loop).
    """
    food_path = data_dir / "food.csv"
    nutrient_path = data_dir / "food_nutrient.csv"
    branded_path = data_dir / "branded_food.csv"
    if not food_path.exists() or not nutrient_path.exists():
        return None
    with _open(nutrient_path) as fh:
        nutrients = parse_nutrients(fh)
    branded: dict[str, dict[str, str]] = {}
    if branded_path.exists():
        with _open(branded_path) as fh:
            branded = parse_branded(fh)
    with _open(food_path) as fh:
        return list(normalize_foods(fh, nutrients, branded))


async def ingest_dir(data_dir: Path) -> int:
    """Ingest the CSVs already present in ``data_dir``. Returns rows written.

    Expects ``food.csv`` + ``food_nutrient.csv`` (and optionally
    ``branded_food.csv``). Run ``download_fdc_bundle`` first on the VPS to
    populate ``data_dir``.
    """
    log = get_logger("ingest.usda")
    foods = await asyncio.to_thread(load_normalized, data_dir)
    if foods is None:
        log.warning("usda_csvs_missing", data_dir=str(data_dir))
        return 0
    log.info("usda_parsed", food_rows=len(foods))

    sm = get_sessionmaker()
    written = 0
    async with sm() as session:
        written += await upsert_stream(session, foods)
        written += await upsert_stream(session, branded_barcode_rows(foods))
    log.info("usda_ingest_done", rows_written=written)
    return written


async def main() -> None:
    configure_logging()
    data_dir = Path(os.environ.get("USDA_DATA_DIR", str(DEFAULT_DATA_DIR)))
    try:
        await ingest_dir(data_dir)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
