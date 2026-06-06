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
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


@dataclass(frozen=True)
class ProbeResult:
    """One probed endpoint: what we sent and what came back."""

    label: str
    method: str
    url: str
    status: int | None
    ok: bool
    # A trimmed snippet of the JSON body (or text/error) so we can read the shape.
    body_snippet: Any
    error: str | None = None


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
# Probe (TEMPORARY, spike-only)
# ---------------------------------------------------------------------------

# Endpoint candidates to try with a real token. The docs conflict on version
# (v1 vs v4) and on the exact path/verb for reading data points and listing
# data types, so we try several and report which return 200 + a body snippet.
# Whatever wins here defines the real shape we build Phase 2 against.
_PROBE_CANDIDATES: list[tuple[str, str, str]] = [
    (
        "weight_dataPoints_v4",
        "GET",
        f"{API_BASE}/v4/users/me/dataTypes/com.google.weight/dataPoints",
    ),
    (
        "weight_dataPoints_v1",
        "GET",
        f"{API_BASE}/v1/users/me/dataTypes/com.google.weight/dataPoints",
    ),
    ("dataTypes_list_v4", "GET", f"{API_BASE}/v4/users/me/dataTypes"),
    ("dataTypes_list_v1", "GET", f"{API_BASE}/v1/users/me/dataTypes"),
    # A couple of alternate shapes the docs hint at (dataSources / sessions).
    ("dataSources_v1", "GET", f"{API_BASE}/v1/users/me/dataSources"),
    ("sessions_v1", "GET", f"{API_BASE}/v1/users/me/sessions"),
]

_PROBE_SNIPPET_CHARS = 1500


def _snippet(body: Any) -> Any:
    """Trim a body for reporting: keep JSON structure but cap string length."""
    text = body if isinstance(body, str) else repr(body)
    if len(text) > _PROBE_SNIPPET_CHARS:
        return text[:_PROBE_SNIPPET_CHARS] + f"... (+{len(text) - _PROBE_SNIPPET_CHARS} chars)"
    return body


async def probe_data(*, access_token: str) -> list[ProbeResult]:
    """Hit every candidate endpoint once with the bearer token and capture the
    status + a body snippet for each. Never raises: the whole point is to see
    raw responses (including 404/400) so we can learn the real API surface.
    """
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    results: list[ProbeResult] = []
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        for label, method, url in _PROBE_CANDIDATES:
            try:
                response = await client.request(method, url, headers=headers)
                try:
                    parsed: Any = response.json()
                except ValueError:
                    parsed = response.text
                results.append(
                    ProbeResult(
                        label=label,
                        method=method,
                        url=url,
                        status=response.status_code,
                        ok=response.is_success,
                        body_snippet=_snippet(parsed),
                    )
                )
            except httpx.HTTPError as exc:
                results.append(
                    ProbeResult(
                        label=label,
                        method=method,
                        url=url,
                        status=None,
                        ok=False,
                        body_snippet=None,
                        error=repr(exc),
                    )
                )
    return results
