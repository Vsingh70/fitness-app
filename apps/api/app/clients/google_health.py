"""Thin async client for Google's OAuth 2.0 + the Google Health API.

Part of the Fitbit -> Google Health migration. Provides a PKCE OAuth connect
flow plus typed readers for body measurements (weight, body-fat) and the daily
metrics (steps, resting HR, HRV, sleep) we sync into ``daily_metrics``.

Design: module-level functions, no global httpx client, so tests can
monkeypatch the module functions directly.

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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 8.0
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5
# Safety cap on dataPoint pagination so a runaway nextPageToken can't loop forever.
# dataPoints come newest-first; with the client-side early-stop in _list_data_points
# (bounded by a per-reader ``since``), 25 pages comfortably covers an incremental
# window even for minute-level metrics (steps, heart-rate). The cap only bites on
# a first/backfill sync, which BACKFILL_DAYS keeps to a reasonable span.
MAX_PAGES = 25

# First-sync window for high-frequency metrics (no last_synced_at yet).
BACKFILL_DAYS = 30
# Re-read this much recent history every sync to catch late-arriving/edited data.
OVERLAP = timedelta(days=2)


def compute_since(last_synced_at: datetime | None) -> datetime:
    """Lower bound for an incremental read.

    First sync (``last_synced_at`` is None): now - BACKFILL_DAYS. Otherwise read
    from ``last_synced_at`` minus OVERLAP so recently-edited days are re-pulled.
    """
    now = datetime.now(tz=UTC)
    if last_synced_at is None:
        return now - timedelta(days=BACKFILL_DAYS)
    return last_synced_at - OVERLAP


AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://health.googleapis.com"

SCOPE_PREFIX = "https://www.googleapis.com/auth/"
# Read-only health scopes (without the prefix, for convenience).
HEALTH_METRICS_SCOPE = "googlehealth.health_metrics_and_measurements.readonly"
ACTIVITY_SCOPE = "googlehealth.activity_and_fitness.readonly"
SLEEP_SCOPE = "googlehealth.sleep.readonly"
ECG_SCOPE = "googlehealth.ecg.readonly"

# Default fully-qualified scope list (health scopes + openid for an id_token).
DEFAULT_SCOPES = [
    SCOPE_PREFIX + HEALTH_METRICS_SCOPE,
    SCOPE_PREFIX + ACTIVITY_SCOPE,
    SCOPE_PREFIX + SLEEP_SCOPE,
    SCOPE_PREFIX + ECG_SCOPE,
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
                # A 400 with "invalid_grant" means the refresh token is dead (e.g. a
                # 7-day Testing-mode token expired). Classify it as auth, not transient,
                # so callers can prompt a reconnect instead of retrying forever.
                if response.status_code == 400 and "invalid_grant" in response.text:
                    raise GoogleHealthAuthError(
                        f"google token endpoint returned invalid_grant: {response.text}"
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


async def _get_data_points_page(
    *, access_token: str, data_type: str, page_token: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch a single page of dataPoints. Returns (points, nextPageToken).

    Raises GoogleHealthAuthError on 401/403; returns ([], None) on any other 4xx
    (no data / type unsupported) so a partial sync never hard-fails; raises
    GoogleHealthClientError on network/parse failure after retries.
    """
    url = f"{API_BASE}/v4/users/me/dataTypes/{data_type}/dataPoints"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    params = {"pageToken": page_token} if page_token else None
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code in (401, 403):
                    raise GoogleHealthAuthError(
                        f"google health returned {response.status_code} on {data_type}"
                    )
                if 400 <= response.status_code < 500:
                    logger.warning(
                        "google_health_data_4xx",
                        extra={"data_type": data_type, "status": response.status_code},
                    )
                    return [], None
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    return [], None
                points = body.get("dataPoints")
                next_token = body.get("nextPageToken")
                return (
                    points if isinstance(points, list) else [],
                    next_token if isinstance(next_token, str) and next_token else None,
                )
        except GoogleHealthAuthError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise GoogleHealthClientError(f"GET {data_type} dataPoints failed: {last_exc!r}")


async def _list_data_points(
    *,
    access_token: str,
    data_type: str,
    since: datetime | None = None,
    point_time: Callable[[dict[str, Any]], datetime | None] | None = None,
) -> list[dict[str, Any]]:
    """List dataPoints for a dataType, following nextPageToken across pages.

    dataPoints are returned NEWEST-FIRST. When ``since`` and ``point_time`` are
    both provided, we early-stop: after a full page whose every point is OLDER
    than ``since`` (none newer-or-equal), all further pages are older too, so we
    stop. A point whose timestamp can't be parsed counts as "keep going" so one
    malformed point never truncates the read. With ``point_time`` None the
    behavior is unchanged (full pagination to MAX_PAGES).

    Capped at MAX_PAGES to avoid an unbounded loop; logs a warning if the cap is
    hit so silent truncation is visible. A mid-pagination 4xx stops paging and
    returns whatever was collected so far; 401/403 still raise.
    """
    collected: list[dict[str, Any]] = []
    page_token: str | None = None
    for _page in range(MAX_PAGES):
        points, page_token = await _get_data_points_page(
            access_token=access_token, data_type=data_type, page_token=page_token
        )
        collected.extend(points)
        if page_token is None:
            return collected
        # Early-stop only after a FULL page has no point newer-or-equal to ``since``
        # (guards against a single old point mid-page). Unparseable times (None)
        # count as "keep going" so one malformed point never truncates the read.
        if (
            since is not None
            and point_time is not None
            and points
            and not any((t := point_time(p)) is None or t >= since for p in points)
        ):
            return collected
    logger.warning(
        "google_health_pagination_cap",
        extra={"data_type": data_type, "max_pages": MAX_PAGES, "collected": len(collected)},
    )
    return collected


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


def _weight_point_time(pt: dict[str, Any]) -> datetime | None:
    w = pt.get("weight") if isinstance(pt, dict) else None
    return _parse_time(w.get("sampleTime")) if isinstance(w, dict) else None


def _body_fat_point_time(pt: dict[str, Any]) -> datetime | None:
    bf = pt.get("bodyFat") if isinstance(pt, dict) else None
    return _parse_time(bf.get("sampleTime")) if isinstance(bf, dict) else None


async def list_weight(
    *, access_token: str, since: datetime | None = None
) -> list[HealthMeasurement]:
    """Read weight readings (e.g. from a Fitbit Aria scale)."""
    out: list[HealthMeasurement] = []
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=WEIGHT_DATA_TYPE,
        since=since,
        point_time=_weight_point_time,
    ):
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


async def list_body_fat(
    *, access_token: str, since: datetime | None = None
) -> list[HealthMeasurement]:
    """Read body-fat percentage readings, if the scale reports them.

    The exact value field for body-fat wasn't captured in the spike; we read
    defensively from the likely keys and skip anything we can't parse.
    """
    out: list[HealthMeasurement] = []
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=BODY_FAT_DATA_TYPE,
        since=since,
        point_time=_body_fat_point_time,
    ):
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
# Daily metric reads (confirmed against a live account 2026-06-07).
#
# All four bucket per the user's LOCAL day. Source timestamps are ISO UTC and
# carry a separate utcOffset string like "-14400s"; we apply that offset to get
# the local calendar date a value belongs to. Each reader returns PARTIAL
# DailySummary rows (only its own field filled); the service merges by date.
#   steps (id "steps"):                  point.steps.interval.startTime,
#                                        point.steps.count STRING -> SUM/local day
#   heart-rate (id "heart-rate"):        point.heartRate.sampleTime.physicalTime,
#                                        beatsPerMinute STRING -> MIN/local day (resting_hr)
#   HRV (id "heart-rate-variability"):   point.heartRateVariability.sampleTime.physicalTime,
#                                        rootMeanSquare...Milliseconds NUMBER -> mean/local day
#   sleep (id "sleep"):                  point.sleep.interval.startTime/endTime,
#                                        summary.minutesAsleep STRING; keyed to local END date
# ---------------------------------------------------------------------------

STEPS_DATA_TYPE = "steps"
HEART_RATE_DATA_TYPE = "heart-rate"
HRV_DATA_TYPE = "heart-rate-variability"
SLEEP_DATA_TYPE = "sleep"


@dataclass(frozen=True)
class DailySummary:
    """A partial per-day aggregate from one Google Health dataType reader.

    Each reader fills only its own field; the service merges rows by date.
    """

    date: date
    steps: int | None = None
    resting_hr: int | None = None
    hrv_ms: Decimal | None = None
    sleep_minutes: int | None = None


def _to_int(value: Any) -> int | None:
    """Defensive int() for STRING source fields. None on anything unparseable."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_offset_seconds(offset: Any) -> int:
    """Parse a utcOffset string like "-14400s" into seconds. 0 on anything odd."""
    if not isinstance(offset, str) or not offset.endswith("s"):
        return 0
    try:
        return int(offset[:-1])
    except ValueError:
        return 0


def _local_date(iso_utc: Any, offset: Any) -> date | None:
    """Convert an ISO-UTC timestamp + utcOffset string into the LOCAL calendar
    date the value belongs to. Returns None if the timestamp can't be parsed.
    """
    if not isinstance(iso_utc, str):
        return None
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local_tz = timezone(timedelta(seconds=_parse_offset_seconds(offset)))
    return dt.astimezone(local_tz).date()


def _parse_iso_utc(iso: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware UTC datetime. None if unparseable."""
    if not isinstance(iso, str):
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _steps_point_time(pt: dict[str, Any]) -> datetime | None:
    steps = pt.get("steps") if isinstance(pt, dict) else None
    interval = steps.get("interval") if isinstance(steps, dict) else None
    return _parse_iso_utc(interval.get("startTime")) if isinstance(interval, dict) else None


def _heart_rate_point_time(pt: dict[str, Any]) -> datetime | None:
    hr = pt.get("heartRate") if isinstance(pt, dict) else None
    sample_time = hr.get("sampleTime") if isinstance(hr, dict) else None
    return (
        _parse_iso_utc(sample_time.get("physicalTime")) if isinstance(sample_time, dict) else None
    )


def _hrv_point_time(pt: dict[str, Any]) -> datetime | None:
    hrv = pt.get("heartRateVariability") if isinstance(pt, dict) else None
    sample_time = hrv.get("sampleTime") if isinstance(hrv, dict) else None
    return (
        _parse_iso_utc(sample_time.get("physicalTime")) if isinstance(sample_time, dict) else None
    )


def _sleep_point_time(pt: dict[str, Any]) -> datetime | None:
    sleep = pt.get("sleep") if isinstance(pt, dict) else None
    interval = sleep.get("interval") if isinstance(sleep, dict) else None
    return _parse_iso_utc(interval.get("endTime")) if isinstance(interval, dict) else None


async def list_steps(*, access_token: str, since: datetime | None = None) -> list[DailySummary]:
    """Daily step totals: SUM of per-minute counts, bucketed to the local day."""
    totals: dict[date, int] = {}
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=STEPS_DATA_TYPE,
        since=since,
        point_time=_steps_point_time,
    ):
        steps = pt.get("steps") if isinstance(pt, dict) else None
        if not isinstance(steps, dict):
            continue
        interval = steps.get("interval")
        if not isinstance(interval, dict):
            continue
        day = _local_date(interval.get("startTime"), interval.get("startUtcOffset"))
        count = _to_int(steps.get("count"))
        if day is None or count is None:
            continue
        totals[day] = totals.get(day, 0) + count
    return [DailySummary(date=d, steps=v) for d, v in totals.items()]


async def list_heart_rate(
    *, access_token: str, since: datetime | None = None
) -> list[DailySummary]:
    """Resting HR proxy: MIN beatsPerMinute per local day (no resting-HR type)."""
    mins: dict[date, int] = {}
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=HEART_RATE_DATA_TYPE,
        since=since,
        point_time=_heart_rate_point_time,
    ):
        hr = pt.get("heartRate") if isinstance(pt, dict) else None
        if not isinstance(hr, dict):
            continue
        sample_time = hr.get("sampleTime")
        offset = sample_time.get("utcOffset") if isinstance(sample_time, dict) else None
        physical = sample_time.get("physicalTime") if isinstance(sample_time, dict) else None
        day = _local_date(physical, offset)
        bpm = _to_int(hr.get("beatsPerMinute"))
        if day is None or bpm is None:
            continue
        prev = mins.get(day)
        if prev is None or bpm < prev:
            mins[day] = bpm
    return [DailySummary(date=d, resting_hr=v) for d, v in mins.items()]


async def list_hrv(*, access_token: str, since: datetime | None = None) -> list[DailySummary]:
    """HRV: mean RMSSD (ms) per local day. The rmssd value is a NUMBER."""
    sums: dict[date, Decimal] = {}
    counts: dict[date, int] = {}
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=HRV_DATA_TYPE,
        since=since,
        point_time=_hrv_point_time,
    ):
        hrv = pt.get("heartRateVariability") if isinstance(pt, dict) else None
        if not isinstance(hrv, dict):
            continue
        sample_time = hrv.get("sampleTime")
        offset = sample_time.get("utcOffset") if isinstance(sample_time, dict) else None
        physical = sample_time.get("physicalTime") if isinstance(sample_time, dict) else None
        day = _local_date(physical, offset)
        if day is None:
            continue
        try:
            rmssd = Decimal(str(hrv.get("rootMeanSquareOfSuccessiveDifferencesMilliseconds")))
        except (TypeError, ValueError, InvalidOperation):
            continue
        sums[day] = sums.get(day, Decimal(0)) + rmssd
        counts[day] = counts.get(day, 0) + 1
    out: list[DailySummary] = []
    for d, total in sums.items():
        mean = (total / Decimal(counts[d])).quantize(Decimal("0.01"))
        out.append(DailySummary(date=d, hrv_ms=mean))
    return out


async def list_sleep(*, access_token: str, since: datetime | None = None) -> list[DailySummary]:
    """Sleep minutes: one session per night, keyed to the local date it ENDS."""
    out: list[DailySummary] = []
    for pt in await _list_data_points(
        access_token=access_token,
        data_type=SLEEP_DATA_TYPE,
        since=since,
        point_time=_sleep_point_time,
    ):
        sleep = pt.get("sleep") if isinstance(pt, dict) else None
        if not isinstance(sleep, dict):
            continue
        interval = sleep.get("interval")
        if not isinstance(interval, dict):
            continue
        day = _local_date(interval.get("endTime"), interval.get("endUtcOffset"))
        summary = sleep.get("summary")
        minutes = _to_int(summary.get("minutesAsleep")) if isinstance(summary, dict) else None
        if day is None or minutes is None:
            continue
        out.append(DailySummary(date=day, sleep_minutes=minutes))
    return out


# ---------------------------------------------------------------------------
# ECG discovery probe (TEMPORARY, spike-only).
#
# ECG needs the googlehealth.ecg.readonly scope (added to DEFAULT_SCOPES) AND a
# re-consent. We don't know the dataType ID, the payload shape, or whether Google
# exposes ECG waveforms to third-party apps at all. This sweeps candidate IDs and
# logs the full first dataPoint to the server log (PROBE_SHAPE <id> <json>) so we
# can read the result off the box. REMOVE after we decide build-vs-revert.
# ---------------------------------------------------------------------------

_ECG_PROBE_DATA_TYPES: list[str] = [
    "ecg",
    "electrocardiogram",
    "ecg-reading",
    "ecg-voltage",
    "ecg-classification",
    "electrocardiogram-voltage",
]


@dataclass(frozen=True)
class ProbeResult:
    """One probed ECG dataType: what came back."""

    data_type: str
    status: int | None
    ok: bool
    point_count: int | None
    sample: Any
    error: str | None = None


async def probe_ecg_data_types(*, access_token: str) -> list[ProbeResult]:
    """GET each candidate ECG dataType and report status + first-point shape.
    Best-effort: never raises for a single response; one sweep reveals the real
    ID + shape (or that ECG is unavailable). Logs full JSON to the server log."""
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    results: list[ProbeResult] = []
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        for data_type in _ECG_PROBE_DATA_TYPES:
            url = f"{API_BASE}/v4/users/me/dataTypes/{data_type}/dataPoints"
            try:
                response = await client.get(url, headers=headers)
                status = response.status_code
                if status == 200:
                    body = response.json()
                    raw = body.get("dataPoints") if isinstance(body, dict) else None
                    points: list[Any] = raw if isinstance(raw, list) else []
                    count = len(points)
                    sample = points[0] if count else "(no dataPoints)"
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
                            sample=response.text[:300],
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
