"""Thin async client around Ollama's /api/generate endpoint.

One function, no pooling, no streaming. Tests monkeypatch `generate` directly.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import get_settings
from app.observability.metrics import (
    OLLAMA_REQUEST_DURATION_SECONDS,
    OLLAMA_REQUESTS_TOTAL,
)
from app.observability.spans import traced_span

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MODEL = "qwen2.5:7b-instruct"
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5


class OllamaError(RuntimeError):
    """Raised when Ollama fails after all retries (network, 5xx, or invalid JSON)."""


DEFAULT_VISION_TIMEOUT_SECONDS = 60.0
DEFAULT_VISION_MODEL = "llava:13b"


async def generate_vision(
    *,
    prompt: str,
    images: list[bytes],
    system: str | None = None,
    model: str = DEFAULT_VISION_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 512,
    format_json: bool = True,
    timeout_seconds: float = DEFAULT_VISION_TIMEOUT_SECONDS,
    user_id: Any | None = None,
) -> str:
    """Call Ollama's vision endpoint with one or more images.

    Each entry in `images` is the raw bytes of a JPEG/PNG. We base64-encode
    them per Ollama's API spec. `format_json=True` tells Ollama to constrain
    output to JSON.
    """
    import base64

    base_url = get_settings().ollama_url.rstrip("/")
    encoded = [base64.b64encode(b).decode("ascii") for b in images]
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "images": encoded,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if system is not None:
        payload["system"] = system
    if format_json:
        payload["format"] = "json"

    with traced_span(
        "ai.ollama.vision",
        user_id=user_id,
        attributes={"ollama.model": model, "ollama.image_count": len(images)},
    ):
        started = time.perf_counter()
        last_exc: Exception | None = None
        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                        response = await client.post(f"{base_url}/api/generate", json=payload)
                        response.raise_for_status()
                        data = response.json()
                        text = data.get("response")
                        if not isinstance(text, str):
                            raise OllamaError(
                                f"Ollama response missing 'response' string: {data!r}"
                            )
                        OLLAMA_REQUESTS_TOTAL.labels(
                            endpoint="generate_vision", model=model, outcome="success"
                        ).inc()
                        return text.strip()
                except (httpx.HTTPError, OllamaError, ValueError) as exc:
                    last_exc = exc
                    if attempt + 1 < RETRY_ATTEMPTS:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
            outcome = "timeout" if isinstance(last_exc, httpx.TimeoutException) else "error"
            OLLAMA_REQUESTS_TOTAL.labels(
                endpoint="generate_vision", model=model, outcome=outcome
            ).inc()
            raise OllamaError(
                f"Ollama vision request failed after {RETRY_ATTEMPTS} attempts: {last_exc!r}"
            )
        finally:
            OLLAMA_REQUEST_DURATION_SECONDS.labels(endpoint="generate_vision", model=model).observe(
                time.perf_counter() - started
            )


async def generate(
    *,
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 120,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    user_id: Any | None = None,
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

    with traced_span("ai.ollama.chat", user_id=user_id, attributes={"ollama.model": model}):
        started = time.perf_counter()
        last_exc: Exception | None = None
        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                        response = await client.post(f"{base_url}/api/generate", json=payload)
                        response.raise_for_status()
                        data = response.json()
                        text = data.get("response")
                        if not isinstance(text, str):
                            raise OllamaError(
                                f"Ollama response missing 'response' string: {data!r}"
                            )
                        OLLAMA_REQUESTS_TOTAL.labels(
                            endpoint="generate", model=model, outcome="success"
                        ).inc()
                        return text.strip()
                except (httpx.HTTPError, OllamaError, ValueError) as exc:
                    last_exc = exc
                    if attempt + 1 < RETRY_ATTEMPTS:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
            outcome = "timeout" if isinstance(last_exc, httpx.TimeoutException) else "error"
            OLLAMA_REQUESTS_TOTAL.labels(endpoint="generate", model=model, outcome=outcome).inc()
            raise OllamaError(
                f"Ollama request failed after {RETRY_ATTEMPTS} attempts: {last_exc!r}"
            )
        finally:
            OLLAMA_REQUEST_DURATION_SECONDS.labels(endpoint="generate", model=model).observe(
                time.perf_counter() - started
            )
