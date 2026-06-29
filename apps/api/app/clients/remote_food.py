"""Shared shape for a food fetched from a live external search provider.

The USDA FoodData Central and Open Food Facts search clients both return these so
the foods service can cache them into ``foods`` with one code path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RemoteFood:
    source: str  # FoodSource value: "usda" | "off"
    external_id: str  # FDC id or barcode — the cache key with source
    name: str
    brand: str | None = None
    serving_size_g: Decimal | None = None
    serving_label: str | None = None
    kcal_per_100g: Decimal | None = None
    protein_g_per_100g: Decimal | None = None
    carbs_g_per_100g: Decimal | None = None
    fat_g_per_100g: Decimal | None = None
    fiber_g_per_100g: Decimal | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def has_macros(self) -> bool:
        return any(
            v is not None
            for v in (
                self.kcal_per_100g,
                self.protein_g_per_100g,
                self.carbs_g_per_100g,
                self.fat_g_per_100g,
            )
        )
