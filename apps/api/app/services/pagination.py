import base64
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException


def encode_cursor(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if cursor is None:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode())
        parsed = json.loads(raw.decode())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Invalid cursor.")
    return parsed


def encode_created_at_id_cursor(created_at: datetime, item_id: UUID) -> str:
    return encode_cursor({"c": created_at.isoformat(), "i": str(item_id)})


def decode_created_at_id_cursor(
    cursor: str | None,
) -> tuple[datetime, UUID] | None:
    payload = decode_cursor(cursor)
    if payload is None:
        return None
    try:
        return datetime.fromisoformat(payload["c"]), UUID(payload["i"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
