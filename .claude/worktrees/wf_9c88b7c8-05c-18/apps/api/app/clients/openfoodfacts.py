"""Thin async wrapper around the Open Food Facts product API.

Tests monkeypatch `fetch_product` directly to control responses.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 4.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.25
USER_AGENT = "gym-app/0.1 (https://github.com/anthropics/claude-code)"


class OffNotFoundError(Exception):
    """OFF returned status 0 (product not found in their DB)."""


class OffClientError(Exception):
    """Network or unexpected response shape after retries."""


@dataclass(frozen=True)
class OffProduct:
    barcode: str
    name: str
    brand: str | None
    serving_size_g: Decimal | None
    serving_label: str | None
    kcal_per_100g: Decimal | None
    protein_g_per_100g: Decimal | None
    carbs_g_per_100g: Decimal | None
    fat_g_per_100g: Decimal | None
    fiber_g_per_100g: Decimal | None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return None


def _parse(barcode: str, body: dict[str, Any]) -> OffProduct:
    """Map OFF v2 response into our domain object.

    OFF stores per-100g nutrients under product.nutriments with keys like
    energy-kcal_100g, proteins_100g, carbohydrates_100g, fat_100g, fiber_100g.
    """
    product = body.get("product") or {}
    nutriments = product.get("nutriments") or {}
    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or product.get("generic_name")
        or "Unknown product"
    )
    brand = product.get("brands")
    if isinstance(brand, str) and "," in brand:
        brand = brand.split(",", 1)[0].strip()

    serving_size_raw = product.get("serving_quantity")
    serving_label = product.get("serving_size")
    return OffProduct(
        barcode=barcode,
        name=str(name)[:240],
        brand=str(brand)[:160] if brand else None,
        serving_size_g=_to_decimal(serving_size_raw),
        serving_label=str(serving_label) if serving_label else None,
        kcal_per_100g=_to_decimal(nutriments.get("energy-kcal_100g")),
        protein_g_per_100g=_to_decimal(nutriments.get("proteins_100g")),
        carbs_g_per_100g=_to_decimal(nutriments.get("carbohydrates_100g")),
        fat_g_per_100g=_to_decimal(nutriments.get("fat_100g")),
        fiber_g_per_100g=_to_decimal(nutriments.get("fiber_100g")),
    )


async def fetch_product(
    barcode: str, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> OffProduct:
    """Look up a barcode on OFF. Raises OffNotFoundError if status==0,
    OffClientError on any network failure after retries.
    """
    base = "https://world.openfoodfacts.org/api/v2/product"
    url = f"{base}/{barcode}.json"
    headers = {"User-Agent": USER_AGENT}
    # Allow override via settings if a future per-env staging host is added.
    override = getattr(get_settings(), "openfoodfacts_base_url", None)
    if override:
        url = f"{override.rstrip('/')}/api/v2/product/{barcode}.json"

    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    raise OffNotFoundError(f"barcode {barcode} not found on OFF")
                response.raise_for_status()
                body = response.json()
                status = body.get("status")
                if status == 0 or body.get("status_verbose", "").lower().startswith(
                    "product not found"
                ):
                    raise OffNotFoundError(f"barcode {barcode} not found on OFF")
                return _parse(barcode, body)
        except OffNotFoundError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise OffClientError(f"OFF lookup failed after {RETRY_ATTEMPTS} attempts: {last_exc!r}")
