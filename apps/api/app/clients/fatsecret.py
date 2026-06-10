"""Async client for the FatSecret Platform API (nutrition search + detail).

Replaces the USDA seed as the primary search source. Provides text search,
full food detail (with the servings list), and barcode lookup, normalized into
our ``foods`` + ``food_servings`` schema.

Design mirrors ``app/clients/google_health.py`` / ``app/clients/openfoodfacts.py``:
module-level functions, no global httpx client, so tests monkeypatch the module
functions directly. Credentials follow the Google Health secret pattern: read
from ``Settings``; if unset we raise ``FatSecretConfigError`` so callers can
degrade to the OFF/custom path instead of 500ing.

TIER NOTE: the configured FatSecret app key is BASIC tier (verified live). The
``basic`` scope works; ``premier`` and ``barcode`` return ``invalid_scope`` at the
token endpoint. So we use the basic-tier methods ``foods.search`` (v1) and
``food.get.v2`` for search + detail (both verified to return real foods + servings
with gram weights). Upgrading the FatSecret app to premier would unlock
``foods.search.v3`` / ``food.get.v4`` / ``food.find_id_for_barcode``; until then
barcode lookups get a missing-scope error and we fall back to Open Food Facts.

API FACTS (verified; build to these):
- Auth: OAuth 2.0 client credentials. POST to the token endpoint with HTTP Basic
  (client_id:client_secret) and body ``grant_type=client_credentials&scope=basic``.
  Returns a bearer access_token + ``expires_in``; we cache it in-process and
  refresh on expiry.
- REST: POST to the server endpoint with ``Authorization: Bearer <token>`` and
  params ``method=<method>&format=json`` plus method args. JSON responses.
- Methods wrapped: ``foods.search`` (v1), ``food.get.v2``, ``food.find_id_for_barcode``.
- Errors: a failed call returns an ``error`` object in the JSON body (e.g. invalid
  token, rate limit, "unknown method"/"missing scope" when a method needs a higher
  tier).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
API_URL = "https://platform.fatsecret.com/rest/server.api"
# This key is basic tier: only the ``basic`` scope is granted. Requesting
# ``premier``/``barcode`` makes the token endpoint return 400 invalid_scope.
DEFAULT_SCOPE = "basic"

DEFAULT_TIMEOUT_SECONDS = 8.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5
# Refresh the cached token this long before it actually expires so an in-flight
# call never races the expiry boundary.
TOKEN_EXPIRY_SKEW = timedelta(seconds=30)

# FatSecret error codes that mean "this method/scope isn't available on our tier"
# (e.g. barcode on a basic key). We treat these like a miss and fall through.
# 3 = unknown method, 4 = method not allowed, 14 = missing scope (e.g. 'barcode').
_UNKNOWN_METHOD_CODES = {3, 4, 14}


class FatSecretConfigError(RuntimeError):
    """Credentials are not configured. Callers should fall back to OFF/custom."""


class FatSecretClientError(RuntimeError):
    """Network or unexpected response shape after retries."""


class FatSecretAuthError(RuntimeError):
    """Token endpoint returned 401/403, or a data call reported an auth error."""


class FatSecretMethodNotAllowedError(RuntimeError):
    """FatSecret reported the method as unknown/not permitted for our tier.

    Raised for barcode lookups on a key without the barcode scope so the caller
    can degrade gracefully (treat like a miss, fall through to OFF).
    """


class FatSecretNotFoundError(RuntimeError):
    """A lookup (barcode / food id) resolved to no food."""


# ---------------------------------------------------------------------------
# Domain objects (normalized into our schema)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FatSecretSearchHit:
    """A single ``foods.search`` result (summary only; no servings yet)."""

    food_id: str
    name: str
    brand: str | None


@dataclass(frozen=True)
class FatSecretServing:
    """One serving option normalized for ``food_servings``.

    ``grams`` is the resolved gram weight of one of this serving. For an ``ml``
    metric with no density we treat 1 ml as 1 g (documented approximation).
    """

    description: str
    metric_amount: Decimal | None
    metric_unit: str | None  # "g" | "ml" | None
    grams: Decimal | None
    is_default: bool


@dataclass(frozen=True)
class FatSecretFood:
    """A fully-resolved food: per-100g macros + every serving."""

    food_id: str
    name: str
    brand: str | None
    kcal_per_100g: Decimal | None
    protein_g_per_100g: Decimal | None
    carbs_g_per_100g: Decimal | None
    fat_g_per_100g: Decimal | None
    fiber_g_per_100g: Decimal | None
    servings: list[FatSecretServing] = field(default_factory=list)


# ---------------------------------------------------------------------------
# In-process token cache
# ---------------------------------------------------------------------------


@dataclass
class _CachedToken:
    access_token: str
    expires_at: datetime


_token_cache: _CachedToken | None = None
_token_lock = asyncio.Lock()


def _clear_token_cache() -> None:
    """Drop the cached bearer token so the next call refetches one."""
    global _token_cache
    _token_cache = None


def reset_token_cache_for_tests() -> None:
    """Test helper: clear the cached bearer token between tests."""
    _clear_token_cache()


def _credentials() -> tuple[str, str]:
    settings = get_settings()
    client_id = settings.fatsecret_client_id
    client_secret = settings.fatsecret_client_secret
    if not client_id or not client_secret:
        raise FatSecretConfigError(
            "fatsecret_client_id / fatsecret_client_secret are not configured"
        )
    return client_id, client_secret


async def _fetch_token() -> _CachedToken:
    """Fetch a fresh bearer token via OAuth 2.0 client credentials."""
    client_id, client_secret = _credentials()
    form = {"grant_type": "client_credentials", "scope": DEFAULT_SCOPE}
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(TOKEN_URL, data=form, auth=(client_id, client_secret))
                if response.status_code in (401, 403):
                    raise FatSecretAuthError(
                        f"fatsecret token endpoint returned {response.status_code}"
                    )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict) or "access_token" not in body:
                    raise FatSecretClientError("token response missing access_token")
                expires_in = int(body.get("expires_in") or 0)
                return _CachedToken(
                    access_token=str(body["access_token"]),
                    expires_at=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
                )
        except (FatSecretAuthError, FatSecretConfigError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise FatSecretClientError(f"fatsecret token call failed: {last_exc!r}")


async def _access_token() -> str:
    """Return a valid bearer token, fetching/refreshing through the cache.

    A module-level lock makes concurrent first-calls fetch the token once.
    """
    global _token_cache
    now = datetime.now(tz=UTC)
    cached = _token_cache
    if cached is not None and cached.expires_at - TOKEN_EXPIRY_SKEW > now:
        return cached.access_token
    async with _token_lock:
        # Re-check inside the lock: another coroutine may have refreshed it.
        cached = _token_cache
        if cached is not None and cached.expires_at - TOKEN_EXPIRY_SKEW > now:
            return cached.access_token
        token = await _fetch_token()
        _token_cache = token
        return token.access_token


# ---------------------------------------------------------------------------
# Low-level REST call
# ---------------------------------------------------------------------------


def _raise_for_api_error(body: dict[str, Any]) -> None:
    """Map a FatSecret ``error`` object to our exception types."""
    error = body.get("error")
    if not isinstance(error, dict):
        return
    code = error.get("code")
    message = str(error.get("message") or "fatsecret error")
    code_int: int | None
    try:
        code_int = int(code) if code is not None else None
    except (TypeError, ValueError):
        code_int = None
    lowered = message.lower()
    # 3/4 = unknown/disallowed method, 14 = missing scope (e.g. 'barcode' on a
    # basic key) → degrade gracefully so the caller can fall through to OFF.
    if (
        code_int in _UNKNOWN_METHOD_CODES
        or "unknown method" in lowered
        or "missing scope" in lowered
    ):
        raise FatSecretMethodNotAllowedError(message)
    # 12/13/21 = invalid/expired/missing auth token → genuine auth failures.
    if code_int in (12, 13, 21) or "token" in lowered:
        raise FatSecretAuthError(message)
    raise FatSecretClientError(f"fatsecret error {code}: {message}")


async def _call(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """POST a single method to the REST endpoint. Returns the parsed JSON body.

    Retries transient failures; refreshes the token once on an auth error
    (covers an expired cached token). Raises the mapped exception types.
    """
    auth_retried = False
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        token = await _access_token()
        call_params = {"method": method, "format": "json", **params}
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(API_URL, params=call_params, headers=headers)
                if response.status_code in (401, 403) and not auth_retried:
                    _clear_token_cache()
                    auth_retried = True
                    continue
                if response.status_code in (401, 403):
                    raise FatSecretAuthError(f"fatsecret {method} returned {response.status_code}")
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise FatSecretClientError(f"{method} response was not a JSON object")
                _raise_for_api_error(body)
                return body
        except FatSecretAuthError:
            if not auth_retried:
                _clear_token_cache()
                auth_retried = True
                continue
            raise
        except (FatSecretMethodNotAllowedError, FatSecretConfigError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise FatSecretClientError(f"fatsecret {method} failed: {last_exc!r}")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _as_list(value: Any) -> list[dict[str, Any]]:
    """FatSecret returns a single object instead of a 1-element list. Normalize."""
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _normalize_unit(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    unit = raw.strip().lower()
    if unit in ("g", "gram", "grams"):
        return "g"
    if unit in ("ml", "milliliter", "milliliters", "millilitre", "millilitres"):
        return "ml"
    return None


def _parse_serving(raw: dict[str, Any]) -> FatSecretServing:
    """Map a FatSecret serving object to our normalized serving.

    Resolved grams: prefer the metric gram amount; for an ml metric with no
    density we treat 1 ml as 1 g (documented water-equivalent assumption).
    """
    description = str(raw.get("serving_description") or raw.get("measurement_description") or "")[
        :240
    ]
    metric_amount = _to_decimal(raw.get("metric_serving_amount"))
    metric_unit = _normalize_unit(raw.get("metric_serving_unit"))
    grams: Decimal | None = None
    if metric_amount is not None and metric_unit in ("g", "ml"):
        # g → grams directly; ml → assume 1 ml ≈ 1 g (no density available).
        grams = metric_amount
    is_default = str(raw.get("is_default") or "0") == "1"
    return FatSecretServing(
        description=description or "1 serving",
        metric_amount=metric_amount,
        metric_unit=metric_unit,
        grams=grams,
        is_default=is_default,
    )


def _per_100g(serving_value: Decimal | None, grams: Decimal | None) -> Decimal | None:
    """Scale a per-serving macro to per-100g using the serving's gram weight."""
    if serving_value is None or grams is None or grams == 0:
        return None
    return (serving_value / grams * Decimal(100)).quantize(Decimal("0.01"))


def _parse_food(raw: dict[str, Any]) -> FatSecretFood:
    """Map a ``food.get.v2`` ``food`` object into our normalized food.

    Normalization: compute per-100g macros from a gram-based serving (prefer an
    existing "100 g" serving). Persist ALL servings with their resolved grams.
    """
    food_id = str(raw.get("food_id") or "")
    name = str(raw.get("food_name") or "Unknown food")[:240]
    brand = raw.get("brand_name")
    brand = str(brand)[:160] if brand else None

    servings_raw = raw.get("servings") or {}
    serving_dicts = _as_list(
        servings_raw.get("serving") if isinstance(servings_raw, dict) else servings_raw
    )
    servings = [_parse_serving(s) for s in serving_dicts]

    # Pick the gram-based serving to normalize macros from: prefer one that is
    # exactly 100 g, else any gram serving, else any serving with resolved grams.
    macro_source: dict[str, Any] | None = None
    macro_grams: Decimal | None = None
    for raw_serving, parsed in zip(serving_dicts, servings, strict=True):
        if parsed.grams is None:
            continue
        is_100g = parsed.metric_unit == "g" and parsed.grams == Decimal(100)
        if is_100g:
            macro_source, macro_grams = raw_serving, parsed.grams
            break
        if macro_source is None:
            macro_source, macro_grams = raw_serving, parsed.grams

    if macro_source is not None and macro_grams is not None:
        kcal = _per_100g(_to_decimal(macro_source.get("calories")), macro_grams)
        protein = _per_100g(_to_decimal(macro_source.get("protein")), macro_grams)
        carbs = _per_100g(_to_decimal(macro_source.get("carbohydrate")), macro_grams)
        fat = _per_100g(_to_decimal(macro_source.get("fat")), macro_grams)
        fiber = _per_100g(_to_decimal(macro_source.get("fiber")), macro_grams)
    else:
        kcal = protein = carbs = fat = fiber = None

    return FatSecretFood(
        food_id=food_id,
        name=name,
        brand=brand,
        kcal_per_100g=kcal,
        protein_g_per_100g=protein,
        carbs_g_per_100g=carbs,
        fat_g_per_100g=fat,
        fiber_g_per_100g=fiber,
        servings=servings,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search_foods(
    query: str, *, page_number: int = 0, max_results: int = 20
) -> list[FatSecretSearchHit]:
    """Text search (``foods.search`` v1). Returns summary hits (no servings).

    The v1 response is ``{"foods": {"food": [...], "max_results", "page_number",
    "total_results"}}`` where ``food`` is a list or a single dict for one result.
    """
    body = await _call(
        "foods.search",
        {
            "search_expression": query,
            "page_number": page_number,
            "max_results": max_results,
        },
    )
    foods = body.get("foods")
    food_dicts = _as_list(foods.get("food") if isinstance(foods, dict) else None)
    hits: list[FatSecretSearchHit] = []
    for f in food_dicts:
        food_id = f.get("food_id")
        name = f.get("food_name")
        if not food_id or not name:
            continue
        brand = f.get("brand_name")
        hits.append(
            FatSecretSearchHit(
                food_id=str(food_id),
                name=str(name)[:240],
                brand=str(brand)[:160] if brand else None,
            )
        )
    return hits


async def get_food(food_id: str) -> FatSecretFood:
    """Full detail (``food.get.v2``) including the servings list.

    v2 shares the same ``food``/``servings.serving`` structure as v4 (it just
    lacks the v4 images/allergens fields, which we don't use), so ``_parse_food``
    handles it unchanged.
    """
    body = await _call("food.get.v2", {"food_id": food_id})
    food = body.get("food")
    if not isinstance(food, dict):
        raise FatSecretNotFoundError(f"food {food_id} not found")
    return _parse_food(food)


def _pad_barcode(barcode: str) -> str:
    """FatSecret wants a GTIN-13. Pad UPC-A (12) / EAN-8 with leading zeros."""
    digits = "".join(ch for ch in barcode if ch.isdigit())
    return digits.zfill(13)


async def find_food_id_for_barcode(barcode: str) -> str:
    """Resolve a barcode to a FatSecret food id (``food.find_id_for_barcode``).

    This basic-tier key lacks the ``barcode`` scope, so FatSecret returns a
    missing-scope error (code 14) which surfaces as
    ``FatSecretMethodNotAllowedError`` — the caller falls through to OFF. A real
    miss (on a key that had the scope) surfaces as ``FatSecretNotFoundError``.
    """
    try:
        body = await _call("food.find_id_for_barcode", {"barcode": _pad_barcode(barcode)})
    except FatSecretMethodNotAllowedError:
        logger.info(
            "fatsecret_barcode_method_unavailable",
            extra={"barcode": barcode},
        )
        raise
    food_id_obj = body.get("food_id")
    value = food_id_obj.get("value") if isinstance(food_id_obj, dict) else food_id_obj
    # FatSecret returns "0" for "no match".
    if value is None or str(value) in ("", "0"):
        raise FatSecretNotFoundError(f"barcode {barcode} not found on fatsecret")
    return str(value)


async def lookup_barcode(barcode: str) -> FatSecretFood:
    """Barcode dance: find_id_for_barcode → food.get.v2. Returns the full food."""
    food_id = await find_food_id_for_barcode(barcode)
    return await get_food(food_id)
