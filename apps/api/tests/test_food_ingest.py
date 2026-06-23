"""Food-data ingest: USDA + OFF normalization and idempotent UPSERT.

Pure-parse tests use small inline fixtures (no multi-GB downloads). The
``download_*`` functions are intentionally not exercised here. The UPSERT tests
hit the real ``foods`` table to prove ``(source, external_id)`` idempotency.
"""

from __future__ import annotations

import gzip
import io
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from app.db import get_sessionmaker
from app.models.enums import FoodSource
from scripts.ingest import off as off_ingest
from scripts.ingest import usda as usda_ingest
from scripts.ingest.common import NormalizedFood, to_decimal, upsert_foods

# --- USDA parse -----------------------------------------------------------

FOOD_CSV = """fdc_id,data_type,description,food_category_id
1001,foundation_food,"Chicken, breast, raw",5
1002,sr_legacy_food,"Egg, whole, raw",1
1003,branded_food,"ACME Protein Bar",10
1004,agricultural_acquisition,"Should be skipped",99
"""

FOOD_NUTRIENT_CSV = """id,fdc_id,nutrient_id,amount
1,1001,1008,165
2,1001,1003,31
3,1001,1005,0
4,1001,1004,3.6
5,1002,1008,143
6,1002,1003,12.6
7,1003,1008,400
8,1003,1003,20
9,1003,1079,3
"""

BRANDED_CSV = """fdc_id,brand_owner,gtin_upc,serving_size,serving_size_unit
1003,ACME Foods,0049000028904,40,g
"""


def test_usda_normalize_tags_category_and_macros() -> None:
    nutrients = usda_ingest.parse_nutrients(io.StringIO(FOOD_NUTRIENT_CSV))
    branded = usda_ingest.parse_branded(io.StringIO(BRANDED_CSV))
    foods = list(usda_ingest.normalize_foods(io.StringIO(FOOD_CSV), nutrients, branded))

    by_id = {f.external_id: f for f in foods}
    # Skipped the non-ingested data type.
    assert "1004" not in by_id
    assert set(by_id) == {"1001", "1002", "1003"}

    chicken = by_id["1001"]
    assert chicken.source is FoodSource.usda
    assert chicken.payload == {"category": "foundation_food"}
    assert chicken.kcal_per_100g == Decimal("165.00")
    assert chicken.protein_g_per_100g == Decimal("31.00")

    bar = by_id["1003"]
    assert bar.payload["category"] == "branded_food"
    assert bar.payload["gtin_upc"] == "0049000028904"
    assert bar.brand == "ACME Foods"
    assert bar.serving_size_g == Decimal("40.00")


def test_usda_branded_barcode_projection() -> None:
    nutrients = usda_ingest.parse_nutrients(io.StringIO(FOOD_NUTRIENT_CSV))
    branded = usda_ingest.parse_branded(io.StringIO(BRANDED_CSV))
    foods = list(usda_ingest.normalize_foods(io.StringIO(FOOD_CSV), nutrients, branded))

    barcode_rows = list(usda_ingest.branded_barcode_rows(foods))
    # Only the branded row with a GTIN is projected.
    assert len(barcode_rows) == 1
    row = barcode_rows[0]
    assert row.source is FoodSource.usda
    assert row.external_id == "0049000028904"
    assert row.payload["fdc_id"] == "1003"
    assert row.kcal_per_100g == Decimal("400.00")


# --- OFF parse ------------------------------------------------------------


def _off_line(**over: object) -> str:
    base = {
        "code": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero, Nutella",
        "serving_size": "15 g",
        "serving_quantity": 15,
        "nutriments": {
            "energy-kcal_100g": 539,
            "proteins_100g": 6.3,
            "carbohydrates_100g": 57.5,
            "fat_100g": 30.9,
            "fiber_100g": 0,
        },
    }
    base.update(over)
    return json.dumps(base)


def test_off_parse_keeps_lean_fields() -> None:
    food = off_ingest.parse_product(json.loads(_off_line()))
    assert food is not None
    assert food.source is FoodSource.off
    assert food.external_id == "3017620422003"
    assert food.name == "Nutella"
    assert food.brand == "Ferrero"  # first brand only
    assert food.kcal_per_100g == Decimal("539.00")
    assert food.serving_size_g == Decimal("15.00")
    assert food.payload == {}


def test_off_skips_rows_without_barcode_name_or_macros() -> None:
    # No barcode.
    assert off_ingest.parse_product(json.loads(_off_line(code=""))) is None
    # No name.
    assert off_ingest.parse_product(json.loads(_off_line(product_name=""))) is None
    # No usable macros.
    assert off_ingest.parse_product(json.loads(_off_line(nutriments={}))) is None


def test_off_iter_normalized_streams_and_skips_junk() -> None:
    lines = [
        _off_line(code="111", product_name="Good"),
        "not json at all",
        "",
        _off_line(code="", product_name="No barcode"),
        _off_line(code="222", product_name="Also good"),
    ]
    foods = list(off_ingest.iter_normalized(lines))
    assert [f.external_id for f in foods] == ["111", "222"]


def test_off_iter_dump_lines_reads_gzip(tmp_path: Path) -> None:
    path = tmp_path / "dump.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(_off_line(code="999") + "\n")
    lines = list(off_ingest.iter_dump_lines(path))
    assert len(lines) == 1
    assert json.loads(lines[0])["code"] == "999"


# --- common normalization -------------------------------------------------


def test_to_decimal_clamps_and_drops_junk() -> None:
    # 2dp quantize (banker's rounding): 12.345 -> 12.34.
    assert to_decimal("12.345") == Decimal("12.34")
    assert to_decimal("12.50") == Decimal("12.50")
    assert to_decimal("") is None
    assert to_decimal(None) is None
    assert to_decimal("-5") is None  # negative junk dropped
    assert to_decimal("not a number") is None
    # Clamped to the Numeric(7,2) ceiling.
    assert to_decimal("999999999") == Decimal("99999.99")


# --- UPSERT idempotency (DB) ----------------------------------------------


async def _count(source: str, external_id: str) -> int:
    sm = get_sessionmaker()
    async with sm() as db:
        res = await db.execute(
            text("SELECT COUNT(*) FROM foods WHERE source = :s AND external_id = :e"),
            {"s": source, "e": external_id},
        )
        return int(res.scalar_one())


async def _macro(source: str, external_id: str) -> Decimal | None:
    sm = get_sessionmaker()
    async with sm() as db:
        res = await db.execute(
            text("SELECT kcal_per_100g FROM foods WHERE source = :s AND external_id = :e"),
            {"s": source, "e": external_id},
        )
        return res.scalar_one()


async def test_upsert_is_idempotent_on_source_external_id() -> None:
    food = NormalizedFood(
        source=FoodSource.usda,
        external_id="UPSERT1",
        name="Test Food",
        kcal_per_100g=Decimal("100.00"),
        payload={"category": "foundation_food"},
    )
    sm = get_sessionmaker()
    async with sm() as db:
        assert await upsert_foods(db, [food]) == 1
        await db.commit()
    assert await _count("usda", "UPSERT1") == 1
    assert await _macro("usda", "UPSERT1") == Decimal("100.00")

    # Re-run with refreshed macros: same row, updated value, no duplicate.
    refreshed = NormalizedFood(
        source=FoodSource.usda,
        external_id="UPSERT1",
        name="Test Food",
        kcal_per_100g=Decimal("250.00"),
        payload={"category": "foundation_food"},
    )
    async with sm() as db:
        await upsert_foods(db, [refreshed])
        await db.commit()
    assert await _count("usda", "UPSERT1") == 1
    assert await _macro("usda", "UPSERT1") == Decimal("250.00")


async def test_upsert_dedupes_within_batch() -> None:
    rows = [
        NormalizedFood(source=FoodSource.off, external_id="DUP", name="v1", kcal_per_100g=Decimal("1")),
        NormalizedFood(source=FoodSource.off, external_id="DUP", name="v2", kcal_per_100g=Decimal("2")),
    ]
    sm = get_sessionmaker()
    async with sm() as db:
        # Last occurrence wins; no "command cannot affect row a second time".
        await upsert_foods(db, rows)
        await db.commit()
    assert await _count("off", "DUP") == 1
    assert await _macro("off", "DUP") == Decimal("2.00")
