"""Tests for POST /v1/meals/recognize and the photo storage + rate limiter."""

from __future__ import annotations

import io
import time
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import text

from app.clients import ollama
from app.db import get_sessionmaker
from app.services import auth as auth_service
from app.services import rate_limit
from app.services.storage import meal_photos


def _jpeg_bytes(
    *, width: int = 400, height: int = 300, color: tuple[int, int, int] = (200, 50, 50)
) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "mp-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_food(name: str) -> None:
    sm = get_sessionmaker()
    async with sm() as db:
        await db.execute(
            text("""
                INSERT INTO foods (id, source, name, payload, created_at, updated_at)
                VALUES (gen_random_uuid(), 'usda', :name, '{}'::jsonb, NOW(), NOW())
                """),
            {"name": name},
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Storage helpers (pure)
# ---------------------------------------------------------------------------


def test_save_meal_photo_strips_exif_and_resizes(tmp_path: Any) -> None:
    """A large JPEG with EXIF should round-trip to <=1024px without EXIF."""
    from uuid import uuid4

    img = Image.new("RGB", (3000, 2000), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=b"Exif\x00\x00mock-data")
    raw = buf.getvalue()

    stored = meal_photos.save_meal_photo(
        user_id=uuid4(),
        raw_bytes=raw,
        content_type="image/jpeg",
        root=tmp_path,
    )
    assert stored.width <= 1024 and stored.height <= 1024
    with Image.open(stored.absolute_path) as out:
        assert (out.getexif() or {}).get(0x0112) is None  # no orientation EXIF
        assert max(out.size) <= 1024


def test_save_meal_photo_rejects_too_large(tmp_path: Any) -> None:
    from uuid import uuid4

    huge = b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(Exception) as exc_info:
        meal_photos.save_meal_photo(
            user_id=uuid4(),
            raw_bytes=huge,
            content_type="image/jpeg",
            root=tmp_path,
        )
    assert getattr(exc_info.value, "status_code", None) == 413


def test_save_meal_photo_rejects_wrong_mime(tmp_path: Any) -> None:
    from uuid import uuid4

    with pytest.raises(Exception) as exc_info:
        meal_photos.save_meal_photo(
            user_id=uuid4(),
            raw_bytes=b"hello world",
            content_type="text/plain",
            root=tmp_path,
        )
    assert getattr(exc_info.value, "status_code", None) == 415


def _age_file(path: Any, days: int) -> None:
    """Backdate a file's mtime (and atime) by ``days`` days."""
    import os

    target = time.time() - days * 86400
    os.utime(path, (target, target))


def test_cleanup_removes_only_old_files_when_enabled(tmp_path: Any) -> None:
    """With cleanup enabled, only files older than the retention window go away."""
    from pathlib import Path

    user_dir = tmp_path / "user-a" / "2026" / "05"
    user_dir.mkdir(parents=True)
    old_photo = user_dir / "old.jpg"
    new_photo = user_dir / "new.jpg"
    old_photo.write_bytes(_jpeg_bytes())
    new_photo.write_bytes(_jpeg_bytes())
    # Old is well past the 30-day window; new is well within it.
    _age_file(old_photo, days=45)
    _age_file(new_photo, days=2)

    result = meal_photos.cleanup_local_photos(root=Path(tmp_path), retention_days=30, enabled=True)

    assert result.enabled is True
    assert result.removed == 1
    assert result.skipped == 1
    assert not old_photo.exists()
    assert new_photo.exists()
    # The now-empty old folder should not be pruned because new.jpg remains.
    assert user_dir.exists()


def test_cleanup_is_noop_when_disabled(tmp_path: Any) -> None:
    """With the flag off, nothing is removed even for ancient files."""
    from pathlib import Path

    user_dir = tmp_path / "user-b" / "2026" / "01"
    user_dir.mkdir(parents=True)
    old_photo = user_dir / "ancient.jpg"
    old_photo.write_bytes(_jpeg_bytes())
    _age_file(old_photo, days=400)

    result = meal_photos.cleanup_local_photos(root=Path(tmp_path), retention_days=30, enabled=False)

    assert result.enabled is False
    assert result.removed == 0
    assert old_photo.exists()


def test_cleanup_prunes_empty_dirs(tmp_path: Any) -> None:
    """Folders left empty after deleting their only photo are pruned."""
    from pathlib import Path

    user_dir = tmp_path / "user-c" / "2025" / "12"
    user_dir.mkdir(parents=True)
    old_photo = user_dir / "lone.jpg"
    old_photo.write_bytes(_jpeg_bytes())
    _age_file(old_photo, days=90)

    result = meal_photos.cleanup_local_photos(root=Path(tmp_path), retention_days=30, enabled=True)

    assert result.removed == 1
    assert not user_dir.exists()
    # Root itself is preserved.
    assert Path(tmp_path).exists()


def test_cleanup_defaults_to_config_flag(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``enabled`` is omitted it follows the config flag (default OFF)."""
    from pathlib import Path

    from app.config import get_settings

    user_dir = tmp_path / "user-d" / "2026" / "02"
    user_dir.mkdir(parents=True)
    old_photo = user_dir / "old.jpg"
    old_photo.write_bytes(_jpeg_bytes())
    _age_file(old_photo, days=60)

    settings = get_settings()
    # Default flag is off -> no-op.
    monkeypatch.setattr(settings, "meal_photo_local_cleanup_enabled", False)
    result = meal_photos.cleanup_local_photos(root=Path(tmp_path))
    assert result.enabled is False
    assert old_photo.exists()

    # Flip the flag on -> deletes the old file.
    monkeypatch.setattr(settings, "meal_photo_local_cleanup_enabled", True)
    monkeypatch.setattr(settings, "meal_photo_retention_days", 30)
    result = meal_photos.cleanup_local_photos(root=Path(tmp_path))
    assert result.enabled is True
    assert result.removed == 1
    assert not old_photo.exists()


def test_signed_url_roundtrips() -> None:
    url = meal_photos.sign_url("user-x/2026/05/abc.jpg", ttl_seconds=60)
    assert "exp=" in url and "sig=" in url
    # Parse exp+sig out
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    exp = int(qs["exp"][0])
    sig = qs["sig"][0]
    assert meal_photos.verify_signed_url("user-x/2026/05/abc.jpg", exp, sig)
    # Tampered sig fails.
    assert not meal_photos.verify_signed_url("user-x/2026/05/abc.jpg", exp, "0" * 64)
    # Expired URL fails.
    assert not meal_photos.verify_signed_url("user-x/2026/05/abc.jpg", int(time.time()) - 1, sig)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


async def test_recognize_good_output_returns_candidates_with_suggestions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    await _seed_food("Grilled Chicken Breast")
    await _seed_food("White Rice")

    async def fake_generate_vision(**kwargs: Any) -> str:
        return (
            '{"caption": "a plate with grilled chicken, white rice, and broccoli",'
            ' "items": ['
            '{"name": "grilled chicken breast", "grams_estimate": 180, "confidence": 0.85},'
            '{"name": "white rice", "grams_estimate": 150, "confidence": 0.7}'
            "]}"
        )

    monkeypatch.setattr(ollama, "generate_vision", fake_generate_vision)

    files = {"photo": ("plate.jpg", _jpeg_bytes(), "image/jpeg")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["raw_caption"].startswith("a plate")
    assert len(body["candidates"]) == 2
    chicken = body["candidates"][0]
    assert chicken["name"] == "grilled chicken breast"
    assert Decimal(chicken["grams_estimate"]) == Decimal("180.0")
    assert Decimal(chicken["confidence"]) == Decimal("0.85")
    # Trigram suggestion should pick up our seeded Grilled Chicken Breast.
    sug_names = [s["name"] for s in chicken["food_id_suggestions"]]
    assert "Grilled Chicken Breast" in sug_names
    # Signed photo URL is present.
    assert body["photo_url"] is not None
    assert "sig=" in body["photo_url"]


async def test_recognize_malformed_llm_output_falls_back(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_generate_vision(**kwargs: Any) -> str:
        return "not even close to JSON"

    monkeypatch.setattr(ollama, "generate_vision", fake_generate_vision)

    files = {"photo": ("plate.jpg", _jpeg_bytes(), "image/jpeg")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidates"] == []
    # Synthetic fallback caption is always present.
    assert isinstance(body["raw_caption"], str) and len(body["raw_caption"]) > 0


async def test_recognize_ollama_outage_returns_fallback(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)

    async def fake_generate_vision(**kwargs: Any) -> str:
        raise ollama.OllamaError("connection refused")

    monkeypatch.setattr(ollama, "generate_vision", fake_generate_vision)

    files = {"photo": ("plate.jpg", _jpeg_bytes(), "image/jpeg")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["candidates"] == []
    assert "manually" in body["raw_caption"].lower()


async def test_recognize_rejects_non_image(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    files = {"photo": ("notes.txt", b"hello world", "text/plain")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 415


async def test_recognize_rejects_oversized_upload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    payload = b"\x00" * (11 * 1024 * 1024)
    files = {"photo": ("huge.jpg", payload, "image/jpeg")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 413


async def test_recognize_concurrency_cap_returns_429(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cap the semaphore at 1 and hold the slot so a second call gets 429."""
    headers = await _sign_in(client, monkeypatch)
    rate_limit.reset_concurrency_for_tests(value=1)

    # Acquire the only slot, then call the endpoint and assert 429.
    async with rate_limit.acquire_photo_slot():
        files = {"photo": ("plate.jpg", _jpeg_bytes(), "image/jpeg")}
        response = await client.post("/v1/meals/recognize", headers=headers, files=files)
        assert response.status_code == 429
        assert response.headers.get("Retry-After") is not None


async def test_recognize_hourly_limit_returns_429(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force the fake Redis to report counts above the limit."""
    headers = await _sign_in(client, monkeypatch)

    class _Over:
        async def incr(self, key: str) -> int:
            return rate_limit.PHOTO_RECOGNIZE_HOURLY_LIMIT + 1

        async def expire(self, key: str, seconds: int) -> bool:
            return True

        async def close(self) -> None:
            return None

    async def fake_get_redis() -> _Over:
        return _Over()

    monkeypatch.setattr(rate_limit, "_get_redis", fake_get_redis)

    files = {"photo": ("plate.jpg", _jpeg_bytes(), "image/jpeg")}
    response = await client.post("/v1/meals/recognize", headers=headers, files=files)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") is not None
