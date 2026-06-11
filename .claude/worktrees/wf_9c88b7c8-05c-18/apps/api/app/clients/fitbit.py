"""Thin async wrapper around Fitbit's Web API.

Tests monkeypatch the module-level functions directly. No global httpx client;
each call opens a fresh AsyncClient so monkeypatching is straightforward.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 8.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5
TOKEN_URL = "https://api.fitbit.com/oauth2/token"
AUTHORIZE_URL = "https://www.fitbit.com/oauth2/authorize"
API_BASE = "https://api.fitbit.com"


class FitbitClientError(RuntimeError):
    """Network or unexpected response shape after retries."""


class FitbitRateLimitedError(RuntimeError):
    """Fitbit returned HTTP 429."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"rate limited, retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class FitbitAuthError(RuntimeError):
    """Fitbit returned HTTP 401 / 403."""


@dataclass(frozen=True)
class FitbitTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]
    fitbit_user_id: str


@dataclass(frozen=True)
class FitbitActivityRow:
    fitbit_log_id: int
    activity_type: str
    started_at: datetime
    duration_seconds: int | None
    calories: int | None
    average_hr: int | None
    max_hr: int | None
    steps: int | None
    distance_meters: Decimal | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class FitbitDailySummary:
    date: date
    steps: int | None
    resting_hr: int | None
    hrv_ms: Decimal | None
    sleep_minutes: int | None
    sleep_score: int | None


def authorize_url(*, state: str, code_challenge: str, scopes: list[str]) -> str:
    """Build the Fitbit authorize URL with PKCE."""
    from urllib.parse import urlencode

    settings = get_settings()
    params = {
        "client_id": settings.fitbit_client_id,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": " ".join(scopes),
        "redirect_uri": settings.fitbit_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _basic_auth_header() -> str:
    settings = get_settings()
    raw = f"{settings.fitbit_client_id}:{settings.fitbit_client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


async def _post_token(form: dict[str, str]) -> dict[str, Any]:
    headers = {
        "Authorization": _basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(TOKEN_URL, data=form, headers=headers)
                if response.status_code == 429:
                    raise FitbitRateLimitedError(int(response.headers.get("Retry-After", "60")))
                if response.status_code in (401, 403):
                    raise FitbitAuthError(f"fitbit token endpoint returned {response.status_code}")
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise FitbitClientError("token response was not a JSON object")
                return body
        except (FitbitAuthError, FitbitRateLimitedError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise FitbitClientError(f"fitbit token call failed: {last_exc!r}")


def _tokens_from_body(body: dict[str, Any]) -> FitbitTokens:
    expires_in = int(body.get("expires_in") or 0)
    scopes_raw = body.get("scope") or ""
    scopes = scopes_raw.split() if isinstance(scopes_raw, str) else list(scopes_raw)
    return FitbitTokens(
        access_token=str(body["access_token"]),
        refresh_token=str(body["refresh_token"]),
        expires_at=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
        scopes=scopes,
        fitbit_user_id=str(body.get("user_id") or ""),
    )


async def exchange_code(
    *, code: str, code_verifier: str, redirect_uri: str | None = None
) -> FitbitTokens:
    redirect = redirect_uri or get_settings().fitbit_redirect_uri
    body = await _post_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "code_verifier": code_verifier,
            "client_id": get_settings().fitbit_client_id,
        }
    )
    return _tokens_from_body(body)


async def refresh_tokens(*, refresh_token: str) -> FitbitTokens:
    body = await _post_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
    return _tokens_from_body(body)


async def revoke(*, access_token: str) -> None:
    """Best-effort revoke. Fitbit returns 200 on success; we swallow errors so
    a disconnect always completes the local cleanup.
    """
    headers = {
        "Authorization": _basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            await client.post(
                f"{API_BASE}/oauth2/revoke",
                data={"token": access_token},
                headers=headers,
            )
    except httpx.HTTPError as exc:
        logger.warning("fitbit_revoke_failed", extra={"error": repr(exc)})


# ---------------------------------------------------------------------------
# Data calls
# ---------------------------------------------------------------------------


async def _get_json(
    *, access_token: str, path: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{API_BASE}{path}", headers=headers, params=params)
                if response.status_code == 429:
                    raise FitbitRateLimitedError(int(response.headers.get("Retry-After", "60")))
                if response.status_code in (401, 403):
                    raise FitbitAuthError(f"fitbit returned {response.status_code} on {path}")
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise FitbitClientError(f"unexpected response shape on {path}")
                return body
        except (FitbitAuthError, FitbitRateLimitedError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise FitbitClientError(f"GET {path} failed: {last_exc!r}")


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (TypeError, ValueError):
        return None


async def list_activities(
    *,
    access_token: str,
    after_date_iso: str,
    limit: int = 100,
) -> list[FitbitActivityRow]:
    """Fitbit activities/list.json: items in reverse chronological order.

    `after_date_iso` is `YYYY-MM-DDTHH:MM:SS`. Pagination via the `next`
    pagination object is left to the caller (we just return the first page).
    """
    body = await _get_json(
        access_token=access_token,
        path="/1/user/-/activities/list.json",
        params={
            "afterDate": after_date_iso,
            "sort": "asc",
            "offset": 0,
            "limit": limit,
        },
    )
    activities = body.get("activities") or []
    out: list[FitbitActivityRow] = []
    for entry in activities:
        if not isinstance(entry, dict):
            continue
        log_id = entry.get("logId")
        if log_id is None:
            continue
        started_at_str = entry.get("startTime")
        try:
            started_at = (
                datetime.fromisoformat(str(started_at_str).replace("Z", "+00:00"))
                if started_at_str
                else None
            )
        except ValueError:
            started_at = None
        if started_at is None:
            continue
        out.append(
            FitbitActivityRow(
                fitbit_log_id=int(log_id),
                activity_type=str(entry.get("activityName") or "unknown")[:120],
                started_at=started_at,
                duration_seconds=_to_int((entry.get("duration") or 0) // 1000) or None,
                calories=_to_int(entry.get("calories")),
                average_hr=_to_int(entry.get("averageHeartRate")),
                max_hr=_to_int(entry.get("heartRateZones", [{}])[-1].get("max"))
                if entry.get("heartRateZones")
                else None,
                steps=_to_int(entry.get("steps")),
                distance_meters=_to_decimal((entry.get("distance") or 0) * 1000)
                if entry.get("distance") is not None
                else None,
                raw=entry,
            )
        )
    return out


@dataclass(frozen=True)
class FitbitPostActivityResult:
    log_id: str
    raw: dict[str, Any]


class FitbitDuplicateError(RuntimeError):
    """Fitbit returned a 409 on activity log creation; the workout is already there."""


async def post_activity(
    *,
    access_token: str,
    activity_id: int,
    start_time: datetime,
    duration_ms: int,
    distance_meters: Decimal | None = None,
    description: str | None = None,
    calories: int | None = None,
) -> FitbitPostActivityResult:
    """POST /1/user/-/activities.json with a finished workout."""
    headers = {"Authorization": f"Bearer {access_token}"}
    local = start_time.astimezone(UTC)
    form: dict[str, str] = {
        "activityId": str(activity_id),
        "startTime": local.strftime("%H:%M:%S"),
        "date": local.strftime("%Y-%m-%d"),
        "durationMillis": str(duration_ms),
    }
    if distance_meters is not None and distance_meters > 0:
        # Fitbit takes kilometers as a float when distance is provided.
        km = (distance_meters / Decimal("1000")).quantize(Decimal("0.01"))
        form["distance"] = str(km)
        form["distanceUnit"] = "km"
    if calories is not None:
        form["manualCalories"] = str(calories)

    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{API_BASE}/1/user/-/activities.json",
                    headers=headers,
                    params=form,
                )
                if response.status_code == 409:
                    raise FitbitDuplicateError("activity already logged")
                if response.status_code == 429:
                    raise FitbitRateLimitedError(int(response.headers.get("Retry-After", "60")))
                if response.status_code in (401, 403):
                    raise FitbitAuthError(
                        f"fitbit returned {response.status_code} on post_activity"
                    )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise FitbitClientError("post_activity response was not a JSON object")
                log = body.get("activityLog") or {}
                log_id = log.get("logId")
                if log_id is None:
                    raise FitbitClientError(f"post_activity missing activityLog.logId: {body!r}")
                if description:
                    await _put_activity_description(
                        access_token=access_token,
                        log_id=int(log_id),
                        description=description,
                    )
                return FitbitPostActivityResult(log_id=str(log_id), raw=body)
        except (FitbitAuthError, FitbitRateLimitedError, FitbitDuplicateError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise FitbitClientError(f"post_activity failed: {last_exc!r}")


async def _put_activity_description(*, access_token: str, log_id: int, description: str) -> None:
    """Best-effort update of the activity description. Swallows errors."""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            await client.post(
                f"{API_BASE}/1/user/-/activities/{log_id}.json",
                headers=headers,
                params={"description": description[:500]},
            )
    except httpx.HTTPError as exc:
        logger.warning("fitbit_put_description_failed", extra={"error": repr(exc)})


async def daily_summary(*, access_token: str, day: date) -> FitbitDailySummary:
    """Pull steps + resting HR + sleep for one day. One call each to the
    minimal endpoints we need; calling code is responsible for batching.
    """
    iso = day.isoformat()
    steps_body = await _get_json(
        access_token=access_token,
        path=f"/1/user/-/activities/steps/date/{iso}/1d.json",
    )
    steps = None
    try:
        steps = int((steps_body.get("activities-steps") or [{}])[-1].get("value") or 0)
    except (ValueError, TypeError, IndexError):
        steps = None

    hr_body = await _get_json(
        access_token=access_token,
        path=f"/1/user/-/activities/heart/date/{iso}/1d.json",
    )
    resting_hr = None
    try:
        entries = hr_body.get("activities-heart") or [{}]
        resting_hr = _to_int((entries[-1].get("value") or {}).get("restingHeartRate"))
    except (TypeError, IndexError):
        resting_hr = None

    sleep_body = await _get_json(
        access_token=access_token,
        path=f"/1.2/user/-/sleep/date/{iso}.json",
    )
    sleep_minutes = None
    sleep_score = None
    summary = sleep_body.get("summary") or {}
    sleep_minutes = _to_int(summary.get("totalMinutesAsleep"))
    sleep_score = _to_int((sleep_body.get("sleep") or [{}])[0].get("efficiency"))

    return FitbitDailySummary(
        date=day,
        steps=steps,
        resting_hr=resting_hr,
        hrv_ms=None,
        sleep_minutes=sleep_minutes,
        sleep_score=sleep_score,
    )
