import base64
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwt

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
