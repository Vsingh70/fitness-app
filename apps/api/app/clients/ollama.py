"""Thin async client around Ollama's /api/generate endpoint.

One function, no pooling, no streaming. Tests monkeypatch `generate` directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MODEL = "qwen2.5:7b-instruct"
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5


class OllamaError(RuntimeError):
    """Raised when Ollama fails after all retries (network, 5xx, or invalid JSON)."""


async def generate(
    *,
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 120,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Call Ollama and return the generated text. Raises OllamaError on failure.

    Uses two attempts with linear backoff. Streaming disabled.
    """
    base_url = get_settings().ollama_url.rstrip("/")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if system is not None:
        payload["system"] = system

    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(f"{base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                text = data.get("response")
                if not isinstance(text, str):
                    raise OllamaError(f"Ollama response missing 'response' string: {data!r}")
                return text.strip()
        except (httpx.HTTPError, OllamaError, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise OllamaError(f"Ollama request failed after {RETRY_ATTEMPTS} attempts: {last_exc!r}")
