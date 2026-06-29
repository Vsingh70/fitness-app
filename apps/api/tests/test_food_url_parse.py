"""URL nutrition import: schema.org JSON-LD parsing + SSRF guard."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException

from app.services import food_url_parse as svc

RECIPE_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Recipe","name":"Protein Pancakes",
 "nutrition":{"@type":"NutritionInformation","calories":"320 kcal",
 "proteinContent":"24 g","carbohydrateContent":"40 g","fatContent":"8 g",
 "fiberContent":"5 g","servingSize":"1 serving (150 g)"}}
</script>
</head><body>recipe</body></html>
"""


async def test_parse_extracts_recipe_nutrition(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str) -> str:
        return RECIPE_HTML

    monkeypatch.setattr(svc, "_fetch_html", fake_fetch)
    parsed = await svc.parse_food_url("https://example.com/recipe")
    assert parsed.name == "Protein Pancakes"
    assert parsed.kcal == Decimal("320")
    assert parsed.protein_g == Decimal("24")
    assert parsed.carbs_g == Decimal("40")
    assert parsed.fat_g == Decimal("8")
    assert parsed.serving_grams == Decimal("150")
    assert parsed.warning is None


async def test_parse_warns_when_serving_grams_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    html = RECIPE_HTML.replace("1 serving (150 g)", "2 cookies")

    async def fake_fetch(url: str) -> str:
        return html

    monkeypatch.setattr(svc, "_fetch_html", fake_fetch)
    parsed = await svc.parse_food_url("https://example.com/recipe")
    assert parsed.kcal == Decimal("320")
    assert parsed.serving_grams is None
    assert parsed.warning is not None


async def test_parse_no_structured_data_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str) -> str:
        return "<html><body>just an article, no nutrition</body></html>"

    monkeypatch.setattr(svc, "_fetch_html", fake_fetch)
    with pytest.raises(HTTPException) as exc:
        await svc.parse_food_url("https://example.com/article")
    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1:8000/v1/health",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file",
        "not-a-url",
    ],
)
def test_validate_url_rejects_unsafe(url: str) -> None:
    with pytest.raises(HTTPException) as exc:
        svc._validate_url(url)
    assert exc.value.status_code == 400


async def test_parse_endpoint_requires_auth(client: Any) -> None:
    resp = await client.post("/v1/foods/parse-url", json={"url": "https://example.com"})
    assert resp.status_code == 401
