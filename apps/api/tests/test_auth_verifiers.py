import asyncio
import base64
import time
from typing import Any
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwt

from app.config import get_settings
from app.services import auth as auth_service


def _int_to_b64url(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    raw = value.to_bytes(byte_length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _generate_jwks_with_key() -> tuple[rsa.RSAPrivateKey, list[dict[str, Any]], str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = key.public_key().public_numbers()
    kid = "test-kid-1"
    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": kid,
        "n": _int_to_b64url(public_numbers.n),
        "e": _int_to_b64url(public_numbers.e),
    }
    return key, [jwk], kid


def _sign_apple_token(
    private_key: rsa.RSAPrivateKey,
    kid: str,
    *,
    audience: str = "com.example.gym.ios",
    sub: str = "apple-sub-1",
    email: str | None = "user@example.com",
    expires_in: int = 600,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": "https://appleid.apple.com",
        "aud": audience,
        "sub": sub,
        "iat": now,
        "exp": now + expires_in,
    }
    if email is not None:
        claims["email"] = email
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


async def test_apple_verify_valid_token() -> None:
    private_key, jwks, kid = _generate_jwks_with_key()
    token = _sign_apple_token(private_key, kid)

    identity = await auth_service.verify_apple_token(token, jwks_override=jwks)
    assert identity.sub == "apple-sub-1"
    assert identity.email == "user@example.com"


async def test_apple_verify_rejects_unknown_kid() -> None:
    private_key, jwks, _ = _generate_jwks_with_key()
    token = _sign_apple_token(private_key, kid="other-kid")

    with pytest.raises(HTTPException) as info:
        await auth_service.verify_apple_token(token, jwks_override=jwks)
    assert info.value.status_code == 401


async def test_apple_verify_rejects_wrong_audience() -> None:
    private_key, jwks, kid = _generate_jwks_with_key()
    token = _sign_apple_token(private_key, kid, audience="com.attacker.app")

    with pytest.raises(HTTPException) as info:
        await auth_service.verify_apple_token(token, jwks_override=jwks)
    assert info.value.status_code == 401


async def test_apple_verify_rejects_expired_token() -> None:
    private_key, jwks, kid = _generate_jwks_with_key()
    token = _sign_apple_token(private_key, kid, expires_in=-60)

    with pytest.raises(HTTPException) as info:
        await auth_service.verify_apple_token(token, jwks_override=jwks)
    assert info.value.status_code == 401


def test_google_verify_calls_library(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_claims = {
        "sub": "google-sub-1",
        "email": "g@example.com",
        "aud": "test-google-client-id.apps.googleusercontent.com",
    }

    def fake_verify(token: str, request: Any) -> dict[str, Any]:
        assert token == "fake-google-token"
        return fake_claims

    monkeypatch.setattr("app.services.auth.google_id_token.verify_oauth2_token", fake_verify)

    identity = auth_service.verify_google_token("fake-google-token")
    assert identity.sub == "google-sub-1"
    assert identity.email == "g@example.com"


def test_google_verify_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(token: str, request: Any) -> dict[str, Any]:
        return {"sub": "x", "aud": "wrong-audience"}

    monkeypatch.setattr("app.services.auth.google_id_token.verify_oauth2_token", fake_verify)

    with pytest.raises(HTTPException) as info:
        auth_service.verify_google_token("fake-google-token")
    assert info.value.status_code == 401


# --- API-3: access-token secret rotation -------------------------------------


def _make_access_token(secret: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": str(uuid4()), "iat": now, "exp": now + 900, "jti": "test-jti"},
        secret,
        algorithm="HS256",
    )


def test_decode_access_token_uses_current_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "current-secret")
    monkeypatch.setenv("JWT_SECRET_PREVIOUS", "previous-secret")
    get_settings.cache_clear()
    try:
        token = _make_access_token("current-secret")
        claims = auth_service.decode_access_token(token)
        assert claims["jti"] == "test-jti"
    finally:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("JWT_SECRET_PREVIOUS", raising=False)
        get_settings.cache_clear()


def test_decode_access_token_falls_back_to_previous_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "current-secret")
    monkeypatch.setenv("JWT_SECRET_PREVIOUS", "previous-secret")
    get_settings.cache_clear()

    warnings: list[dict[str, Any]] = []

    def fake_warning(event: str, **kwargs: Any) -> None:
        warnings.append({"event": event, **kwargs})

    monkeypatch.setattr(auth_service.log, "warning", fake_warning)
    try:
        # Signed with the previous secret: must still verify via the rotation fallback.
        token = _make_access_token("previous-secret")
        claims = auth_service.decode_access_token(token)
        assert claims["jti"] == "test-jti"
        assert any(w["event"] == "access_token_verified_with_previous_secret" for w in warnings), (
            "expected a warning when verifying against the previous secret"
        )
    finally:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("JWT_SECRET_PREVIOUS", raising=False)
        get_settings.cache_clear()


def test_decode_access_token_rejects_when_no_secret_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "current-secret")
    monkeypatch.setenv("JWT_SECRET_PREVIOUS", "previous-secret")
    get_settings.cache_clear()
    try:
        token = _make_access_token("some-other-secret")
        with pytest.raises(HTTPException) as info:
            auth_service.decode_access_token(token)
        assert info.value.status_code == 401
    finally:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("JWT_SECRET_PREVIOUS", raising=False)
        get_settings.cache_clear()


def test_decode_access_token_rejects_when_no_previous_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "current-secret")
    monkeypatch.delenv("JWT_SECRET_PREVIOUS", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().jwt_secret_previous is None
        token = _make_access_token("previous-secret")
        with pytest.raises(HTTPException) as info:
            auth_service.decode_access_token(token)
        assert info.value.status_code == 401
    finally:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        get_settings.cache_clear()


# --- API-10: JWKS stale-while-revalidate + single-flight ---------------------


async def test_apple_jwks_serves_stale_keyset_when_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_key, jwks, _kid = _generate_jwks_with_key()
    auth_service._reset_apple_jwks_cache_for_tests()

    calls = {"n": 0}

    async def flaky_remote(http_client: Any = None) -> list[dict[str, Any]]:
        calls["n"] += 1
        if calls["n"] == 1:
            return jwks
        raise httpx.HTTPError("simulated JWKS fetch failure")

    monkeypatch.setattr(auth_service, "_fetch_apple_jwks_remote", flaky_remote)

    warnings: list[str] = []
    monkeypatch.setattr(
        auth_service.log,
        "warning",
        lambda event, **kwargs: warnings.append(event),
    )

    try:
        # First call populates the cache.
        first = await auth_service._fetch_apple_jwks()
        assert first == jwks

        # Force the cached entry to look expired so the next call attempts a refresh.
        auth_service._apple_jwks_cache["fetched_at"] = (
            time.monotonic() - auth_service.APPLE_JWKS_TTL_SECONDS - 1
        )

        # Refresh fails, but the stale keyset is served instead of raising.
        second = await auth_service._fetch_apple_jwks()
        assert second == jwks
        assert calls["n"] == 2
        assert "apple_jwks_refresh_failed_serving_stale" in warnings
    finally:
        auth_service._reset_apple_jwks_cache_for_tests()


async def test_apple_jwks_raises_when_no_cache_and_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service._reset_apple_jwks_cache_for_tests()

    async def failing_remote(http_client: Any = None) -> list[dict[str, Any]]:
        raise httpx.HTTPError("simulated JWKS fetch failure")

    monkeypatch.setattr(auth_service, "_fetch_apple_jwks_remote", failing_remote)
    try:
        with pytest.raises(httpx.HTTPError):
            await auth_service._fetch_apple_jwks()
    finally:
        auth_service._reset_apple_jwks_cache_for_tests()


async def test_apple_jwks_single_flight_collapses_concurrent_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_key, jwks, _kid = _generate_jwks_with_key()
    auth_service._reset_apple_jwks_cache_for_tests()

    calls = {"n": 0}

    async def slow_remote(http_client: Any = None) -> list[dict[str, Any]]:
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return jwks

    monkeypatch.setattr(auth_service, "_fetch_apple_jwks_remote", slow_remote)
    try:
        results = await asyncio.gather(*(auth_service._fetch_apple_jwks() for _ in range(10)))
        assert all(r == jwks for r in results)
        # Single-flight: a cold cache hit by 10 concurrent callers triggers one fetch.
        assert calls["n"] == 1
    finally:
        auth_service._reset_apple_jwks_cache_for_tests()
