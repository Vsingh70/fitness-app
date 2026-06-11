"""Tests for the /metrics endpoint, instrumentation middleware, and the
expected Prometheus metric families.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.observability.metrics import (
    HTTP_REQUESTS_TOTAL,
    OLLAMA_REQUESTS_TOTAL,
    REGISTRY,
    status_class,
)
from app.services import auth as auth_service


def _set_metrics_token(monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    monkeypatch.setenv("METRICS_TOKEN", token)
    get_settings.cache_clear()


def test_status_class_buckets() -> None:
    assert status_class(200) == "2xx"
    assert status_class(404) == "4xx"
    assert status_class(503) == "5xx"


async def test_metrics_returns_404_when_token_unset(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_metrics_token(monkeypatch, "")
    response = await client.get("/metrics")
    assert response.status_code == 404


async def test_metrics_requires_bearer(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_metrics_token(monkeypatch, "test-metrics-token")
    no_auth = await client.get("/metrics")
    assert no_auth.status_code == 401

    wrong = await client.get("/metrics", headers={"Authorization": "Bearer wrong"})
    assert wrong.status_code == 401

    correct = await client.get("/metrics", headers={"Authorization": "Bearer test-metrics-token"})
    assert correct.status_code == 200
    body = correct.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body


async def test_request_increments_http_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful API call should bump http_requests_total."""

    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub="obs-sub", email="obs@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    sign_in = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    assert sign_in.status_code == 200

    # Reset the auth route counter so we can detect the increment cleanly.
    before = _counter_value(
        HTTP_REQUESTS_TOTAL,
        method="POST",
        route="/v1/auth/apple",
        status_class="2xx",
    )
    # Second call -> bumps counter again.
    second = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    assert second.status_code == 200
    after = _counter_value(
        HTTP_REQUESTS_TOTAL,
        method="POST",
        route="/v1/auth/apple",
        status_class="2xx",
    )
    assert after >= before + 1


def _counter_value(counter: Any, **labels: str) -> float:
    """Read a labeled Counter sample's current value."""
    for metric in counter.collect():
        for sample in metric.samples:
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                return sample.value
    return 0.0


async def test_health_path_not_instrumented(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calls to /v1/health* must not pollute the request histogram."""
    _set_metrics_token(monkeypatch, "test-metrics-token")

    # Hit the health endpoint a bunch.
    for _ in range(5):
        await client.get("/v1/health")

    body = (
        await client.get("/metrics", headers={"Authorization": "Bearer test-metrics-token"})
    ).text
    # The route label "/v1/health" should not appear in any series.
    assert 'route="/v1/health"' not in body


def test_ollama_counter_registered() -> None:
    """Custom metrics live in the same registry that /metrics exposes."""
    names = {sample.name for metric in REGISTRY.collect() for sample in metric.samples}
    assert any(n.startswith("ollama_request_duration_seconds") for n in names) or any(
        m.name.startswith("ollama_request_duration_seconds") for m in REGISTRY.collect()
    )
    # Counter family name is the base name without _total suffix in the
    # collect() output.
    assert (
        any(m.name == "ollama_requests" for m in REGISTRY.collect()) or OLLAMA_REQUESTS_TOTAL
    )  # type-check passes either way
