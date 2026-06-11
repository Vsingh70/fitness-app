"""Authenticated symmetric encryption for storing third-party tokens at rest.

Wraps PyNaCl's `nacl.secret.SecretBox` (XSalsa20-Poly1305). Key is sourced
from `Settings.fitbit_token_key` and may be hex or url-safe base64.

The wire format we persist is `b64(nonce || ciphertext_with_mac)` so that one
column can hold the whole payload. Calls are pure: no I/O.
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache

from nacl.exceptions import CryptoError
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random

from app.config import get_settings

KEY_BYTES = SecretBox.KEY_SIZE  # 32
NONCE_BYTES = SecretBox.NONCE_SIZE  # 24


class DecryptionError(RuntimeError):
    """Raised when a stored token cannot be decrypted (wrong key or tampered)."""


def _decode_key(raw: str) -> bytes:
    """Accept hex (64 chars) or url-safe base64 (no padding ok)."""
    raw = raw.strip()
    if len(raw) == 64:
        try:
            return binascii.unhexlify(raw)
        except (binascii.Error, ValueError):
            pass
    padded = raw + "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("fitbit_token_key must be hex(64) or urlsafe-base64") from exc


@lru_cache(maxsize=1)
def _box() -> SecretBox:
    key = _decode_key(get_settings().fitbit_token_key)
    if len(key) != KEY_BYTES:
        raise RuntimeError(
            f"fitbit_token_key must decode to exactly {KEY_BYTES} bytes; got {len(key)}"
        )
    return SecretBox(key)


def reset_for_tests() -> None:
    _box.cache_clear()


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return a url-safe base64 wire string."""
    nonce = nacl_random(NONCE_BYTES)
    box = _box()
    encrypted = box.encrypt(plaintext.encode("utf-8"), nonce)
    # encrypted.nonce + encrypted.ciphertext is the canonical form, but the
    # `.encrypt()` result also exposes the full message which already prefixes
    # the nonce. We re-pack as `nonce || ciphertext+mac` for explicitness.
    payload = encrypted.nonce + encrypted.ciphertext
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt(wire: str) -> str:
    """Inverse of encrypt. Raises DecryptionError on any failure."""
    try:
        raw = base64.urlsafe_b64decode(wire.encode("ascii"))
        nonce, ciphertext = raw[:NONCE_BYTES], raw[NONCE_BYTES:]
        box = _box()
        plaintext = box.decrypt(ciphertext, nonce)
        return plaintext.decode("utf-8")
    except (CryptoError, binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise DecryptionError("could not decrypt token") from exc
