"""Live USDA FoodData Central search.

Used as a search-time fallback to fill the catalogue on demand (the bulk CSV
ingest isn't run on the small prod box). Covers USDA Branded — e.g. "Just Bare" —
plus Foundation/SR Legacy generics. Needs a free api.data.gov key in
``settings.usda_fdc_api_key``; callers skip this provider when it's unset.

Tests monkeypatch ``search`` directly.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any

import httpx

from app.clients.remote_food import RemoteFood

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 4.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.25
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USER_AGENT = "gym-app/0.1 (https://github.com/anthropics/claude-code)"

# FDC nutrient numbers (strings in the search payload), per 100 g.
_KCAL = "208"
_PROTEIN = "203"
_CARBS = "205"
_FAT = "204"
_FIBER = "291"

# FDC dataType -> our payload.category, which the search ranking uses to tier
# USDA generic (Foundation/SR Legacy) above USDA branded.
_GENERIC_CATEGORY = {
    "foundation": "foundation_food",
    "sr legacy": "sr_legacy_food",
    "survey (fndds)": "sr_legacy_food",
}


class UsdaClientError(Exception):
    """Network or unexpected response shape after retries."""


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return None


def _macros(food: dict[str, Any]) -> dict[str, Decimal | None]:
    by_number: dict[str, Any] = {}
    for nutrient in food.get("foodNutrients") or []:
        number = str(nutrient.get("nutrientNumber") or "")
        if not number:
            continue
        # The search endpoint uses "value"; some shapes use "amount".
        amount = nutrient.get("value", nutrient.get("amount"))
        if number not in by_number and amount is not None:
            by_number[number] = amount
    return {
        "kcal_per_100g": _to_decimal(by_number.get(_KCAL)),
        "protein_g_per_100g": _to_decimal(by_number.get(_PROTEIN)),
        "carbs_g_per_100g": _to_decimal(by_number.get(_CARBS)),
        "fat_g_per_100g": _to_decimal(by_number.get(_FAT)),
        "fiber_g_per_100g": _to_decimal(by_number.get(_FIBER)),
    }


def _parse(food: dict[str, Any]) -> RemoteFood | None:
    fdc_id = food.get("fdcId")
    name = food.get("description")
    if not fdc_id or not name:
        return None
    data_type = str(food.get("dataType") or "").strip().lower()
    category = _GENERIC_CATEGORY.get(data_type, "branded_food")
    brand = food.get("brandName") or food.get("brandOwner")
    serving = _to_decimal(food.get("servingSize"))
    serving_unit = food.get("servingSizeUnit")
    macros = _macros(food)
    remote = RemoteFood(
        source="usda",
        external_id=str(fdc_id),
        name=str(name)[:240],
        brand=str(brand)[:160] if brand else None,
        serving_size_g=serving if (serving_unit or "").lower() in ("g", "gram", "grams") else None,
        serving_label=f"{serving} {serving_unit}" if serving and serving_unit else None,
        payload={"category": category},
        **macros,
    )
    return remote if remote.has_macros else None


async def search(query: str, *, api_key: str, limit: int = 25) -> list[RemoteFood]:
    """Search USDA FDC. Raises UsdaClientError on failure after retries."""
    params: dict[str, Any] = {
        "query": query,
        "dataType": ["Branded", "Foundation", "SR Legacy"],
        "pageSize": max(1, min(limit, 50)),
    }
    # Pass the key as a header (api.data.gov supports X-Api-Key) so it never lands
    # in the request URL — keeps it out of logs and any URL-bearing error messages.
    headers = {"User-Agent": USER_AGENT, "X-Api-Key": api_key}
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.get(SEARCH_URL, params=params, headers=headers)
                response.raise_for_status()
                body = response.json()
                parsed = [_parse(f) for f in body.get("foods") or []]
                return [f for f in parsed if f is not None]
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise UsdaClientError(f"USDA FDC search failed after {RETRY_ATTEMPTS} attempts: {last_exc!r}")
