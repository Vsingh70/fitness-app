"""FatSecret client: token caching/refresh, response parsing + normalization,
error mapping. All HTTP is mocked; the real API is never called.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.clients import fatsecret as fs
from app.config import get_settings


@pytest.fixture(autouse=True)
def _configure_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the client credentials and a clean token cache per test."""
    settings = get_settings()
    monkeypatch.setattr(settings, "fatsecret_client_id", "test-fs-id", raising=False)
    monkeypatch.setattr(settings, "fatsecret_client_secret", "test-fs-secret", raising=False)
    fs.reset_token_cache_for_tests()


class _Resp:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload

    @property
    def text(self) -> str:
        return json.dumps(self._payload)


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token_bodies: list[dict[str, Any]],
    api_bodies: list[dict[str, Any]],
) -> dict[str, list[Any]]:
    """Patch httpx.AsyncClient.post to serve queued token + API responses.

    The token endpoint and the REST endpoint are distinguished by URL. Returns a
    dict capturing token and api calls for assertions.
    """
    calls: dict[str, list[Any]] = {"token": [], "api": []}
    token_queue = list(token_bodies)
    api_queue = list(api_bodies)

    class _FakeClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            data: Any = None,
            params: Any = None,
            headers: Any = None,
            auth: Any = None,
        ) -> _Resp:
            if url == fs.TOKEN_URL:
                calls["token"].append({"data": data, "auth": auth})
                return _Resp(token_queue.pop(0))
            calls["api"].append({"params": params, "headers": headers})
            return _Resp(api_queue.pop(0))

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    return calls


# Token cache --------------------------------------------------------------


async def test_token_cached_and_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok-1", "expires_in": 86400}],
        api_bodies=[
            {"food": {"food_id": "1", "food_name": "A", "servings": {"serving": []}}},
            {"food": {"food_id": "2", "food_name": "B", "servings": {"serving": []}}},
        ],
    )
    await fs.get_food("1")
    await fs.get_food("2")
    # One token fetch despite two API calls (token cached in-process).
    assert len(calls["token"]) == 1
    assert len(calls["api"]) == 2
    # HTTP Basic auth carried the client credentials.
    assert calls["token"][0]["auth"] == ("test-fs-id", "test-fs-secret")


async def test_token_refreshes_on_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_client(
        monkeypatch,
        # First token expires immediately (skew makes it already-stale).
        token_bodies=[
            {"access_token": "tok-1", "expires_in": 0},
            {"access_token": "tok-2", "expires_in": 86400},
        ],
        api_bodies=[
            {"food": {"food_id": "1", "food_name": "A", "servings": {"serving": []}}},
            {"food": {"food_id": "2", "food_name": "B", "servings": {"serving": []}}},
        ],
    )
    await fs.get_food("1")
    await fs.get_food("2")
    # Expired token forces a second fetch.
    assert len(calls["token"]) == 2


async def test_missing_credentials_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "fatsecret_client_id", "", raising=False)
    monkeypatch.setattr(settings, "fatsecret_client_secret", "", raising=False)
    fs.reset_token_cache_for_tests()
    with pytest.raises(fs.FatSecretConfigError):
        await fs.get_food("1")


# Parsing + per-100g normalization -----------------------------------------


def _chicken_food_body() -> dict[str, Any]:
    """food.get.v2 shape with a 100 g serving and a non-gram cup serving."""
    return {
        "food": {
            "food_id": "33691",
            "food_name": "Chicken Breast",
            "brand_name": "Generic",
            "food_type": "Generic",
            "servings": {
                "serving": [
                    {
                        "serving_id": "1",
                        "serving_description": "100 g",
                        "metric_serving_amount": "100.000",
                        "metric_serving_unit": "g",
                        "number_of_units": "100",
                        "measurement_description": "g",
                        "calories": "165",
                        "protein": "31",
                        "carbohydrate": "0",
                        "fat": "3.6",
                        "fiber": "0",
                        "is_default": "1",
                    },
                    {
                        "serving_id": "2",
                        "serving_description": "1 cup, diced",
                        "metric_serving_amount": "140.000",
                        "metric_serving_unit": "g",
                        "number_of_units": "1",
                        "measurement_description": "cup, diced",
                        "calories": "231",
                        "protein": "43.4",
                        "carbohydrate": "0",
                        "fat": "5.04",
                        "fiber": "0",
                    },
                ]
            },
        }
    }


async def test_get_food_normalizes_per_100g_from_gram_serving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[_chicken_food_body()],
    )
    food = await fs.get_food("33691")
    # Basic-tier detail method.
    assert calls["api"][0]["params"]["method"] == "food.get.v2"
    assert food.food_id == "33691"
    assert food.name == "Chicken Breast"
    # 100 g serving → per-100g equals the per-serving values.
    assert food.kcal_per_100g == Decimal("165.00")
    assert food.protein_g_per_100g == Decimal("31.00")
    assert food.fat_g_per_100g == Decimal("3.60")
    # All servings persisted with resolved grams.
    assert len(food.servings) == 2
    by_desc = {s.description: s for s in food.servings}
    assert by_desc["100 g"].grams == Decimal("100.000")
    assert by_desc["100 g"].metric_unit == "g"
    assert by_desc["1 cup, diced"].grams == Decimal("140.000")


async def test_per_100g_computed_when_no_exact_100g_serving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = {
        "food": {
            "food_id": "9",
            "food_name": "Olive Oil",
            "servings": {
                "serving": {
                    "serving_description": "1 tbsp",
                    "metric_serving_amount": "13.500",
                    "metric_serving_unit": "g",
                    "calories": "119",
                    "protein": "0",
                    "carbohydrate": "0",
                    "fat": "13.5",
                }
            },
        }
    }
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[body],
    )
    food = await fs.get_food("9")
    # 119 kcal / 13.5 g * 100 ≈ 881.48
    assert food.kcal_per_100g == Decimal("881.48")
    assert food.fat_g_per_100g == Decimal("100.00")
    # The single serving still resolves to grams.
    assert food.servings[0].grams == Decimal("13.500")


async def test_ml_serving_treated_as_grams(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "food": {
            "food_id": "5",
            "food_name": "Whole Milk",
            "servings": {
                "serving": {
                    "serving_description": "1 cup",
                    "metric_serving_amount": "244.000",
                    "metric_serving_unit": "ml",
                    "calories": "149",
                    "protein": "7.7",
                }
            },
        }
    }
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[body],
    )
    food = await fs.get_food("5")
    serving = food.servings[0]
    assert serving.metric_unit == "ml"
    # 1 ml ≈ 1 g approximation: grams resolves from the ml amount.
    assert serving.grams == Decimal("244.000")
    assert food.kcal_per_100g == Decimal("61.07")  # 149 / 244 * 100


# Search --------------------------------------------------------------------


async def test_search_parses_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    # Basic-tier ``foods.search`` (v1) shape: {"foods": {"food": [...]}}.
    body = {
        "foods": {
            "max_results": "20",
            "page_number": "0",
            "total_results": "2",
            "food": [
                {
                    "food_id": "1",
                    "food_name": "Chicken Breast",
                    "food_type": "Brand",
                    "brand_name": "Tyson",
                    "food_description": "Per 100g - Calories: 165kcal",
                },
                {
                    "food_id": "2",
                    "food_name": "Chicken Thigh",
                    "food_type": "Generic",
                    "food_description": "Per 100g - Calories: 209kcal",
                },
            ],
        }
    }
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[body],
    )
    hits = await fs.search_foods("chicken")
    assert [h.food_id for h in hits] == ["1", "2"]
    assert hits[0].brand == "Tyson"
    assert hits[1].brand is None


async def test_search_single_result_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    # v1 returns a single dict (not a list) when there is exactly one match.
    body = {
        "foods": {
            "max_results": "20",
            "page_number": "0",
            "total_results": "1",
            "food": {
                "food_id": "42",
                "food_name": "Quinoa",
                "food_type": "Generic",
                "food_description": "Per 100g - Calories: 120kcal",
            },
        }
    }
    calls = _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[body],
    )
    hits = await fs.search_foods("quinoa")
    assert [h.food_id for h in hits] == ["42"]
    assert hits[0].brand is None
    # The basic-tier v1 method name was used.
    assert calls["api"][0]["params"]["method"] == "foods.search"


# Barcode + error mapping ---------------------------------------------------


async def test_barcode_missing_scope_raises_method_not_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Basic-tier key lacks the 'barcode' scope: FatSecret returns code 14
    # ("missing scope"), which must degrade to method-not-allowed so the foods
    # service falls through to Open Food Facts (NOT a hard auth error).
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[{"error": {"code": 14, "message": "Missing scope: scope 'barcode'"}}],
    )
    with pytest.raises(fs.FatSecretMethodNotAllowedError):
        await fs.find_food_id_for_barcode("012345678905")


async def test_barcode_unknown_method_raises_method_not_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[{"error": {"code": 3, "message": "Invalid ID: unknown method"}}],
    )
    with pytest.raises(fs.FatSecretMethodNotAllowedError):
        await fs.find_food_id_for_barcode("012345678905")


async def test_barcode_no_match_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[{"food_id": {"value": "0"}}],
    )
    with pytest.raises(fs.FatSecretNotFoundError):
        await fs.find_food_id_for_barcode("012345678905")


async def test_lookup_barcode_resolves_food(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch,
        token_bodies=[{"access_token": "tok", "expires_in": 86400}],
        api_bodies=[{"food_id": {"value": "33691"}}, _chicken_food_body()],
    )
    food = await fs.lookup_barcode("012345678905")
    assert food.food_id == "33691"
    assert any(s.grams is not None for s in food.servings)


async def test_invalid_token_error_maps_to_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Both attempts return an invalid-token error; after a refresh retry it raises.
    _install_fake_client(
        monkeypatch,
        token_bodies=[
            {"access_token": "tok-1", "expires_in": 86400},
            {"access_token": "tok-2", "expires_in": 86400},
        ],
        api_bodies=[
            {"error": {"code": 21, "message": "Invalid token"}},
            {"error": {"code": 21, "message": "Invalid token"}},
        ],
    )
    with pytest.raises(fs.FatSecretAuthError):
        await fs.get_food("1")
