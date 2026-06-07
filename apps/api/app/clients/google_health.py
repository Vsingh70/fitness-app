"""Thin async client for Google's OAuth 2.0 + the Google Health API.

Phase 1 spike: this de-risks the larger Fitbit -> Google Health migration. We
build a real OAuth connect flow (PKCE) and a *probe* that hits several likely
data-read endpoints so we can discover the actual response shapes from a real,
connected account before rewriting the full sync (Phase 2).

Design mirrors ``app/clients/fitbit.py``: module-level functions, no global
httpx client, so tests can monkeypatch the module functions directly.

AUTH FACTS (the public docs conflict, so these are the trusted constants):
- Authorize:  https://accounts.google.com/o/oauth2/v2/auth
- Token:      https://oauth2.googleapis.com/token
- API host:   https://health.googleapis.com
- Read-only scopes VGains needs (prefix https://www.googleapis.com/auth/):
    googlehealth.health_metrics_and_measurements.readonly
    googlehealth.activity_and_fitness.readonly
    googlehealth.sleep.readonly
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 8.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://health.googleapis.com"

SCOPE_PREFIX = "https://www.googleapis.com/auth/"
# Read-only health scopes (without the prefix, for convenience).
HEALTH_METRICS_SCOPE = "googlehealth.health_metrics_and_measurements.readonly"
ACTIVITY_SCOPE = "googlehealth.activity_and_fitness.readonly"
SLEEP_SCOPE = "googlehealth.sleep.readonly"

# Default fully-qualified scope list (health scopes + openid for an id_token).
DEFAULT_SCOPES = [
    SCOPE_PREFIX + HEALTH_METRICS_SCOPE,
    SCOPE_PREFIX + ACTIVITY_SCOPE,
    SCOPE_PREFIX + SLEEP_SCOPE,
    "openid",
]


class GoogleHealthClientError(RuntimeError):
    """Network or unexpected response shape after retries."""


class GoogleHealthAuthError(RuntimeError):
    """Google returned HTTP 401 / 403 on a token or data call."""


@dataclass(frozen=True)
class GoogleHealthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]
    # Google's stable account identifier (the ``sub`` claim), when returned.
    google_user_id: str


def build_authorize_url(*, state: str, code_challenge: str, scopes: list[str]) -> str:
    """Build Google's OAuth 2.0 authorize URL with PKCE.

    ``access_type=offline`` + ``prompt=consent`` guarantee a refresh_token even
    on re-consent. ``include_granted_scopes`` lets incremental auth work later.
    """
    from urllib.parse import urlencode

    settings = get_settings()
    params = {
        "client_id": settings.google_health_client_id,
        "response_type": "code",
        "redirect_uri": settings.google_health_redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def _post_token(form: dict[str, str]) -> dict[str, Any]:
    """POST to Google's token endpoint with retries. client_id/secret go in the
    body (Google accepts both basic-auth and body params; body is simplest).
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(TOKEN_URL, data=form, headers=headers)
                if response.status_code in (401, 403):
                    raise GoogleHealthAuthError(
                        f"google token endpoint returned {response.status_code}: {response.text}"
                    )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise GoogleHealthClientError("token response was not a JSON object")
                return body
        except GoogleHealthAuthError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise GoogleHealthClientError(f"google token call failed: {last_exc!r}")


def _google_user_id_from_body(body: dict[str, Any]) -> str:
    """Best-effort extraction of the stable account id from an id_token's
    ``sub`` claim. We decode the JWT payload without verifying the signature
    (it came straight from Google's TLS-protected token endpoint and is only
    used as a local correlation key, never for auth).
    """
    id_token = body.get("id_token")
    if not isinstance(id_token, str) or id_token.count(".") != 2:
        return ""
    import base64
    import json

    try:
        payload_b64 = id_token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError):
        return ""
    sub = claims.get("sub")
    return str(sub) if sub else ""


def _tokens_from_body(
    body: dict[str, Any], *, fallback_refresh_token: str | None = None
) -> GoogleHealthTokens:
    expires_in = int(body.get("expires_in") or 0)
    scopes_raw = body.get("scope") or ""
    scopes = scopes_raw.split() if isinstance(scopes_raw, str) else list(scopes_raw)
    # On refresh, Google often omits refresh_token; keep the existing one.
    refresh_token = body.get("refresh_token") or fallback_refresh_token or ""
    return GoogleHealthTokens(
        access_token=str(body["access_token"]),
        refresh_token=str(refresh_token),
        expires_at=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
        scopes=scopes,
        google_user_id=_google_user_id_from_body(body),
    )


async def exchange_code(
    *, code: str, code_verifier: str, redirect_uri: str | None = None
) -> GoogleHealthTokens:
    settings = get_settings()
    redirect = redirect_uri or settings.google_health_redirect_uri
    body = await _post_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "code_verifier": code_verifier,
            "client_id": settings.google_health_client_id,
            "client_secret": settings.google_health_client_secret,
        }
    )
    return _tokens_from_body(body)


async def refresh_tokens(*, refresh_token: str) -> GoogleHealthTokens:
    settings = get_settings()
    body = await _post_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.google_health_client_id,
            "client_secret": settings.google_health_client_secret,
        }
    )
    return _tokens_from_body(body, fallback_refresh_token=refresh_token)


# ---------------------------------------------------------------------------
# Data reads (confirmed against a live account 2026-06-07)
#
# GET https://health.googleapis.com/v4/users/me/dataTypes/{type}/dataPoints
# Confirmed dataType ids: "weight", "body-fat" (HYPHEN), "steps".
# Weight point shape:
#   { "name": "...", "dataSource": {...},
#     "weight": { "sampleTime": {"physicalTime": "2026-04-02T13:35:13Z", ...},
#                 "weightGrams": 76658 } }
# ---------------------------------------------------------------------------

WEIGHT_DATA_TYPE = "weight"
BODY_FAT_DATA_TYPE = "body-fat"


@dataclass(frozen=True)
class HealthMeasurement:
    """A body measurement read from Google Health (weight or body-fat)."""

    recorded_at: datetime
    weight_kg: Decimal | None = None
    body_fat_pct: Decimal | None = None


async def _list_data_points(*, access_token: str, data_type: str) -> list[dict[str, Any]]:
    """List raw dataPoints for a dataType. Returns [] on a 4xx (e.g. no data /
    type unsupported) so a partial sync never hard-fails; raises on auth/network.
    """
    url = f"{API_BASE}/v4/users/me/dataTypes/{data_type}/dataPoints"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
                if response.status_code in (401, 403):
                    raise GoogleHealthAuthError(
                        f"google health returned {response.status_code} on {data_type}"
                    )
                if 400 <= response.status_code < 500:
                    logger.warning(
                        "google_health_data_4xx",
                        extra={"data_type": data_type, "status": response.status_code},
                    )
                    return []
                response.raise_for_status()
                body = response.json()
                points = body.get("dataPoints") if isinstance(body, dict) else None
                return points if isinstance(points, list) else []
        except GoogleHealthAuthError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise GoogleHealthClientError(f"GET {data_type} dataPoints failed: {last_exc!r}")


def _parse_time(sample_time: dict[str, Any] | None) -> datetime | None:
    if not isinstance(sample_time, dict):
        return None
    iso = sample_time.get("physicalTime")
    if not isinstance(iso, str):
        return None
    try:
        # physicalTime is ISO-8601 UTC, e.g. "2026-04-02T13:35:13Z".
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


async def list_weight(*, access_token: str) -> list[HealthMeasurement]:
    """Read weight readings (e.g. from a Fitbit Aria scale)."""
    out: list[HealthMeasurement] = []
    for pt in await _list_data_points(access_token=access_token, data_type=WEIGHT_DATA_TYPE):
        w = pt.get("weight") if isinstance(pt, dict) else None
        if not isinstance(w, dict):
            continue
        recorded_at = _parse_time(w.get("sampleTime"))
        grams = w.get("weightGrams")
        if recorded_at is None or grams is None:
            continue
        try:
            kg = Decimal(int(grams)) / Decimal(1000)
        except (TypeError, ValueError):
            continue
        out.append(HealthMeasurement(recorded_at=recorded_at, weight_kg=kg))
    return out


async def list_body_fat(*, access_token: str) -> list[HealthMeasurement]:
    """Read body-fat percentage readings, if the scale reports them.

    The exact value field for body-fat wasn't captured in the spike; we read
    defensively from the likely keys and skip anything we can't parse.
    """
    out: list[HealthMeasurement] = []
    for pt in await _list_data_points(access_token=access_token, data_type=BODY_FAT_DATA_TYPE):
        bf = pt.get("bodyFat") if isinstance(pt, dict) else None
        if not isinstance(bf, dict):
            continue
        recorded_at = _parse_time(bf.get("sampleTime"))
        # Try the most likely percentage fields.
        raw = bf.get("percentage")
        if raw is None:
            raw = bf.get("percent")
        if recorded_at is None or raw is None:
            continue
        try:
            pct = Decimal(str(raw))
        except (TypeError, ValueError):
            continue
        out.append(HealthMeasurement(recorded_at=recorded_at, body_fat_pct=pct))
    return out


# ---------------------------------------------------------------------------
# Discovery probe (TEMPORARY, spike-only) for daily-metric data types.
#
# Only `weight`, `body-fat`, `steps` have confirmed dataType IDs + shapes so far.
# Sleep / resting-HR / HRV / step-detail IDs are unknown (Google's API isn't
# publicly documented), so this sweeps a list of plausible IDs against a real
# connected account and reports status + a trimmed JSON snippet. We read the
# results once to learn the real IDs + payload shapes, then delete this block and
# build the typed readers (mirrors how `weight` was cracked). REMOVE after Phase B.
# ---------------------------------------------------------------------------

# Candidate dataType IDs to sweep. Mix of hyphen/underscore variants and the
# fully-qualified-name styles Google has used, since we don't know the convention
# for these categories yet. The probe reports which return 200 and their shape.
# Second pass: the 4 confirmed-200 types we'll actually sync. We now return the
# FULL first dataPoint (untruncated) to read exact timestamp + value paths.
_PROBE_DATA_TYPES: list[str] = [
    "steps",
    "sleep",
    "heart-rate",
    "heart-rate-variability",
]


@dataclass(frozen=True)
class ProbeResult:
    """One probed dataType: what came back."""

    data_type: str
    status: int | None
    ok: bool
    point_count: int | None
    # A trimmed snippet of the first dataPoint (or error text) to read the shape.
    sample: Any
    error: str | None = None


def _snippet(value: Any, *, limit: int = 1200) -> Any:
    """Trim a JSON value to a readable size for logging."""
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…[truncated]"


async def probe_data_types(*, access_token: str) -> list[ProbeResult]:
    """GET each candidate dataType's dataPoints and report status + first-point
    shape. Best-effort: never raises for a single 4xx; collects everything so one
    sweep reveals all the real IDs + shapes at once."""
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    results: list[ProbeResult] = []
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        for data_type in _PROBE_DATA_TYPES:
            url = f"{API_BASE}/v4/users/me/dataTypes/{data_type}/dataPoints"
            try:
                response = await client.get(url, headers=headers)
                status = response.status_code
                if status == 200:
                    body = response.json()
                    raw_points = body.get("dataPoints") if isinstance(body, dict) else None
                    points: list[Any] = raw_points if isinstance(raw_points, list) else []
                    count = len(points)
                    # Return the FULL first dataPoint as real JSON (no truncation)
                    # so the console shows exact timestamp + value paths.
                    sample = points[0] if count else "(no dataPoints)"
                    # Also dump the full first dataPoint to the server log so the
                    # exact shape can be read off the box without console fishing.
                    # TEMPORARY (spike) — removed with the probe in Phase B.
                    logger.warning(
                        "PROBE_SHAPE %s %s",
                        data_type,
                        json.dumps(points[0]) if count else "(no dataPoints)",
                    )
                    results.append(
                        ProbeResult(
                            data_type=data_type,
                            status=status,
                            ok=True,
                            point_count=count,
                            sample=sample,
                        )
                    )
                else:
                    results.append(
                        ProbeResult(
                            data_type=data_type,
                            status=status,
                            ok=False,
                            point_count=None,
                            sample=_snippet(response.text, limit=300),
                        )
                    )
            except Exception as exc:  # noqa: BLE001 — probe must never hard-fail
                results.append(
                    ProbeResult(
                        data_type=data_type,
                        status=None,
                        ok=False,
                        point_count=None,
                        sample=None,
                        error=repr(exc),
                    )
                )
    return results
