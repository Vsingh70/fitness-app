"""Smoke tests for the custom OpenTelemetry spans added in OBS-4.

Self-contained: we install an in-memory span exporter on a fresh
``TracerProvider`` (swapping it in as the global provider for the duration of
the test, then restoring), exercise instrumented code paths, and assert on the
recorded spans. No real OTLP exporter, no Postgres, no network.

Privacy invariant under test: user ids must appear ONLY as a hashed attribute
(`user_id.hashed`), never as the raw value.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import opentelemetry.trace as trace_api
import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.clients import ollama
from app.observability import spans as spans_module
from app.observability.spans import hash_user_id, traced_arq_job

USER_ID = UUID("11111111-2222-3333-4444-555555555555")

# Capture the genuine generate() at import time, before the autouse
# `stub_rationale_pipeline` fixture (which replaces ollama.generate with a
# raising stub) runs. We want to exercise the real span-wrapped implementation.
_REAL_OLLAMA_GENERATE = ollama.generate


@pytest.fixture
def span_exporter() -> Iterator[InMemorySpanExporter]:
    """Swap in an SDK TracerProvider with an in-memory exporter, restore after."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    saved_provider = trace_api._TRACER_PROVIDER
    saved_once = trace_api._TRACER_PROVIDER_SET_ONCE
    trace_api._TRACER_PROVIDER = provider  # type: ignore[assignment]
    try:
        yield exporter
    finally:
        trace_api._TRACER_PROVIDER = saved_provider  # type: ignore[assignment]
        trace_api._TRACER_PROVIDER_SET_ONCE = saved_once
        provider.shutdown()


def _find_span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan:
    matches = [s for s in exporter.get_finished_spans() if s.name == name]
    assert matches, (
        f"expected a span named {name!r}; got {[s.name for s in exporter.get_finished_spans()]}"
    )
    return matches[0]


async def test_ollama_chat_span_records_hashed_user_id(
    span_exporter: InMemorySpanExporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercising ollama.generate produces an `ai.ollama.chat` span carrying a
    hashed (not raw) user id."""

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"response": "weight goes up by 2.5 kg next session"}

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse()

    monkeypatch.setattr(ollama.httpx, "AsyncClient", _FakeClient)

    result = await _REAL_OLLAMA_GENERATE(prompt="hi", user_id=USER_ID)
    assert result == "weight goes up by 2.5 kg next session"

    span = _find_span(span_exporter, "ai.ollama.chat")
    attrs = dict(span.attributes or {})
    # Hashed, never raw.
    assert attrs.get("user_id.hashed") == hash_user_id(USER_ID)
    assert str(USER_ID) not in attrs.values()
    assert attrs.get("user_id.hashed") != str(USER_ID)


async def test_traced_arq_job_decorator_emits_span_with_hashed_user(
    span_exporter: InMemorySpanExporter,
) -> None:
    """The ARQ decorator names the span after the job and hashes user_id."""

    @traced_arq_job
    async def fitbit_sync_user_task(_ctx: dict[str, Any], user_id: str) -> str:
        return "done"

    out = await fitbit_sync_user_task({}, str(USER_ID))
    assert out == "done"

    span = _find_span(span_exporter, "arq.fitbit_sync_user_task")
    attrs = dict(span.attributes or {})
    assert attrs.get("user_id.hashed") == hash_user_id(str(USER_ID))
    assert str(USER_ID) not in attrs.values()


def test_hash_user_id_is_irreversible_and_short() -> None:
    digest = hash_user_id(USER_ID)
    assert digest is not None
    assert digest != str(USER_ID)
    assert len(digest) == 16
    assert hash_user_id(None) is None


def test_spans_are_noop_without_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no SDK provider, traced_span is a harmless no-op (no exceptions,
    non-recording span)."""
    # Force the proxy/no-op provider for this check.
    monkeypatch.setattr(trace_api, "_TRACER_PROVIDER", None)
    monkeypatch.setattr(trace_api, "_TRACER_PROVIDER_SET_ONCE", trace_api.Once())
    with spans_module.traced_span("ai.ollama.chat", user_id=USER_ID) as span:
        # Setting attributes on a non-recording span must not raise.
        span.set_attribute("user_id.hashed", "ignored")
    assert span.is_recording() is False
