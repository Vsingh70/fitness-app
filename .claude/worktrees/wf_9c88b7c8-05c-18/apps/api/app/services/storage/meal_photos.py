"""Meal photo storage + signed URL helpers.

Layout: `<MEAL_PHOTO_ROOT>/<user_id>/<yyyy>/<mm>/<uuid>.jpg`.

On upload:
- Validate MIME type (jpeg/png/webp/heic).
- Validate size <= MAX_BYTES.
- Open with Pillow, strip EXIF, resize so long edge <= 1024px, save as JPEG q=85.

Signed URLs:
- HMAC-SHA256 over `<path>:<exp>` using `meal_photo_signing_secret`.
- Stored as `?exp=<unix>&sig=<hex>` query string.
- `verify_signed_url(path, exp, sig)` checks expiry first, then constant-time
  comparison on the HMAC.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LONG_EDGE_PX = 1024
JPEG_QUALITY = 85
ALLOWED_MIME_PREFIXES = ("image/jpeg", "image/png", "image/webp", "image/heic")


@dataclass(frozen=True)
class StoredPhoto:
    relative_path: str  # e.g. "<user>/2026/05/<uuid>.jpg"
    absolute_path: Path
    width: int
    height: int
    bytes_written: int


def _validate_upload(content_type: str | None, size: int) -> None:
    if size <= 0:
        raise HTTPException(status_code=400, detail="empty_upload")
    if size > MAX_BYTES:
        raise HTTPException(status_code=413, detail="photo_too_large")
    if content_type is None or not any(
        content_type.lower().startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES
    ):
        raise HTTPException(status_code=415, detail="unsupported_media_type")


def save_meal_photo(
    *,
    user_id: UUID,
    raw_bytes: bytes,
    content_type: str | None,
    root: Path | None = None,
    now: datetime | None = None,
) -> StoredPhoto:
    """Resize, strip EXIF, save under the canonical layout. Returns metadata.

    Raises HTTPException(400/413/415) on bad input.
    """
    _validate_upload(content_type, len(raw_bytes))
    try:
        with Image.open(io.BytesIO(raw_bytes)) as src:
            transposed = ImageOps.exif_transpose(src) or src
            normalized: Image.Image = transposed
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")
            normalized.thumbnail((MAX_LONG_EDGE_PX, MAX_LONG_EDGE_PX), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            normalized.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            jpeg_bytes = buf.getvalue()
            width, height = normalized.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=415, detail="unsupported_media_type") from exc

    root = root or Path(get_settings().meal_photo_root)
    now = now or datetime.now(tz=UTC)
    photo_id = uuid4()
    rel = f"{user_id}/{now:%Y}/{now:%m}/{photo_id}.jpg"
    absolute = root / rel
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(jpeg_bytes)
    return StoredPhoto(
        relative_path=rel,
        absolute_path=absolute,
        width=width,
        height=height,
        bytes_written=len(jpeg_bytes),
    )


# ---------------------------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------------------------


def _hmac(path: str, exp: int) -> str:
    secret = get_settings().meal_photo_signing_secret.encode("utf-8")
    msg = f"{path}:{exp}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def sign_url(relative_path: str, *, ttl_seconds: int | None = None) -> str:
    ttl = ttl_seconds or get_settings().meal_photo_url_ttl_seconds
    exp = int(time.time()) + ttl
    sig = _hmac(relative_path, exp)
    return f"/meal-photos/{relative_path}?exp={exp}&sig={sig}"


def verify_signed_url(relative_path: str, exp: int, sig: str) -> bool:
    if int(time.time()) > exp:
        return False
    expected = _hmac(relative_path, exp)
    return hmac.compare_digest(expected, sig)
