"""Open Food Facts (OFF) nightly dump ingest.

OFF publishes a full database dump as line-delimited JSON, gzipped:
``https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz``
(~9 GB compressed, one JSON product per line). Because it is JSONL we stream it
line by line and never hold the whole file in memory.

We keep only the lean set of fields the app uses — name, brand, serving, per-100g
macros, barcode — and drop products without a usable barcode or any usable
per-100g macro. UPSERT key: ``source='off'``, ``external_id`` = barcode (``code``).

Network/disk: ``download_off_dump`` is the only heavy step and is kept out of the
test path. Tests drive ``parse_product`` + ``iter_normalized`` with small inline
JSONL fixtures.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import httpx

from app.db import dispose_engine, get_sessionmaker
from app.logging_config import configure_logging, get_logger
from app.models.enums import FoodSource

from .common import NormalizedFood, serving_to_decimal, to_decimal, upsert_stream

logger = logging.getLogger(__name__)

OFF_DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
DEFAULT_DUMP_PATH = (
    Path(__file__).resolve().parents[2] / "seed" / "off" / "openfoodfacts-products.jsonl.gz"
)


# ---------------------------------------------------------------------------
# Download (heavy; not exercised by tests)
# ---------------------------------------------------------------------------


def download_off_dump(dest: Path, *, url: str = OFF_DUMP_URL, timeout: float = 3600.0) -> Path:
    """Stream the OFF JSONL.gz dump to ``dest``. The only multi-GB step.

    Kept out of the test path; the runbook runs this off-hours on the VPS.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_bytes(chunk_size=1 << 20):
                fh.write(chunk)
    return dest


# ---------------------------------------------------------------------------
# Parse (pure; tested)
# ---------------------------------------------------------------------------


def _name(product: dict[str, Any]) -> str | None:
    for key in ("product_name", "product_name_en", "generic_name"):
        value = product.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _brand(product: dict[str, Any]) -> str | None:
    brands = product.get("brands")
    if not isinstance(brands, str) or not brands.strip():
        return None
    return brands.split(",", 1)[0].strip()


def parse_product(product: dict[str, Any]) -> NormalizedFood | None:
    """Normalize one OFF product dict to a ``NormalizedFood``.

    Returns None (skip) when the product lacks a barcode, a name, or any usable
    per-100g macro — that culls the long tail of empty crowd-sourced entries the
    spec says we should drop to keep the table lean.
    """
    barcode = product.get("code")
    if not isinstance(barcode, str):
        barcode = str(barcode) if barcode is not None else ""
    barcode = barcode.strip()
    if not barcode:
        return None

    name = _name(product)
    if not name:
        return None

    nutriments = product.get("nutriments") or {}
    if not isinstance(nutriments, dict):
        nutriments = {}
    kcal = to_decimal(nutriments.get("energy-kcal_100g"))
    protein = to_decimal(nutriments.get("proteins_100g"))
    carbs = to_decimal(nutriments.get("carbohydrates_100g"))
    fat = to_decimal(nutriments.get("fat_100g"))
    fiber = to_decimal(nutriments.get("fiber_100g"))
    if all(v is None for v in (kcal, protein, carbs, fat)):
        # No usable macros — not worth a row.
        return None

    serving_label = product.get("serving_size")
    return NormalizedFood(
        source=FoodSource.off,
        external_id=barcode,
        name=name,
        brand=_brand(product),
        serving_size_g=serving_to_decimal(product.get("serving_quantity")),
        serving_label=str(serving_label) if serving_label else None,
        kcal_per_100g=kcal,
        protein_g_per_100g=protein,
        carbs_g_per_100g=carbs,
        fat_g_per_100g=fat,
        fiber_g_per_100g=fiber,
        payload={},
    )


def iter_normalized(lines: Iterable[str]) -> Iterator[NormalizedFood]:
    """Parse a JSONL stream into normalized foods, skipping junk/empty rows."""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            product = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(product, dict):
            continue
        food = parse_product(product)
        if food is not None:
            yield food


def iter_dump_lines(path: Path) -> Iterator[str]:
    """Yield decoded text lines from a (gzipped or plain) JSONL dump."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            yield from fh
    else:
        with open(path, encoding="utf-8") as fh:
            yield from fh


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def ingest_dump(path: Path) -> int:
    """Stream-ingest the OFF dump at ``path``. Returns rows written.

    Run ``download_off_dump`` first on the VPS to populate ``path``.
    """
    log = get_logger("ingest.off")
    if not await asyncio.to_thread(os.path.exists, path):
        log.warning("off_dump_missing", path=str(path))
        return 0
    sm = get_sessionmaker()
    async with sm() as session:
        written = await upsert_stream(session, iter_normalized(iter_dump_lines(path)))
    log.info("off_ingest_done", rows_written=written)
    return written


async def main() -> None:
    configure_logging()
    path = Path(os.environ.get("OFF_DUMP_PATH", str(DEFAULT_DUMP_PATH)))
    try:
        await ingest_dump(path)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
