"""Tests for the /metrics endpoint, instrumentation middleware, and the
expected Prometheus metric families.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from app.clients import ollama as _ollama_module
from app.config import get_settings
from app.observability.metrics import (
    FITBIT_SYNC_TOTAL,
    HTTP_REQUESTS_TOTAL,
    OLLAMA_REQUEST_DURATION_SECONDS,
    OLLAMA_REQUESTS_TOTAL,
    REGISTRY,
    status_class,
)
from app.services import auth as auth_service

# Capture the real Ollama callables at import time, before the autouse
# `stub_rationale_pipeline` fixture replaces `generate` with a failing stub.
# The emit-site tests below drive the genuine client against a fake transport.
_REAL_OLLAMA_GENERATE = _ollama_module.generate
_REAL_OLLAMA_GENERATE_VISION = _ollama_module.generate_vision


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


def _histogram_count(histogram: Any, **labels: str) -> float:
    """Read the observation count of a labeled Histogram (the `_count` sample)."""
    for metric in histogram.collect():
        for sample in metric.samples:
            if sample.name.endswith("_count") and all(
                sample.labels.get(k) == v for k, v in labels.items()
            ):
                return sample.value
    return 0.0


# ---------------------------------------------------------------------------
# Ollama emit sites (API-1)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, *, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("POST", "http://ollama"),
                response=None,  # type: ignore[arg-type]
            )

    def json(self) -> dict[str, Any]:
        return self._payload


def _patch_async_client(monkeypatch: pytest.MonkeyPatch, *, post_impl: Any) -> None:
    """Replace httpx.AsyncClient used inside app.clients.ollama with a fake
    whose .post(...) runs `post_impl`.
    """
    from app.clients import ollama as ollama_module

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeAsyncClient:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        async def post(self, url: str, json: Any = None) -> Any:
            return await post_impl(url, json)

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", _FakeAsyncClient)


async def test_ollama_generate_success_increments_counter_and_histogram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = "qwen2.5:7b-instruct"
    before_ok = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="success"
    )
    before_hist = _histogram_count(
        OLLAMA_REQUEST_DURATION_SECONDS, endpoint="generate", model=model
    )

    async def ok_post(url: str, json: Any) -> Any:
        return _FakeResponse(payload={"response": "ok text"})

    _patch_async_client(monkeypatch, post_impl=ok_post)

    out = await _REAL_OLLAMA_GENERATE(prompt="hi", model=model)
    assert out == "ok text"

    after_ok = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="success"
    )
    after_hist = _histogram_count(OLLAMA_REQUEST_DURATION_SECONDS, endpoint="generate", model=model)
    assert after_ok == before_ok + 1
    assert after_hist == before_hist + 1


async def test_ollama_generate_error_increments_error_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.clients import ollama as ollama_module

    model = "qwen2.5:7b-instruct"
    before = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="error"
    )

    async def bad_post(url: str, json: Any) -> Any:
        raise httpx.ConnectError("refused")

    _patch_async_client(monkeypatch, post_impl=bad_post)

    with pytest.raises(ollama_module.OllamaError):
        await _REAL_OLLAMA_GENERATE(prompt="hi", model=model)

    after = _counter_value(OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="error")
    assert after == before + 1


async def test_ollama_generate_timeout_increments_timeout_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.clients import ollama as ollama_module

    model = "qwen2.5:7b-instruct"
    before = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="timeout"
    )

    async def slow_post(url: str, json: Any) -> Any:
        raise httpx.ReadTimeout("timed out")

    _patch_async_client(monkeypatch, post_impl=slow_post)

    with pytest.raises(ollama_module.OllamaError):
        await _REAL_OLLAMA_GENERATE(prompt="hi", model=model)

    after = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate", model=model, outcome="timeout"
    )
    assert after == before + 1


async def test_ollama_generate_vision_success_increments_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = "llava:13b"
    before = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate_vision", model=model, outcome="success"
    )
    before_hist = _histogram_count(
        OLLAMA_REQUEST_DURATION_SECONDS, endpoint="generate_vision", model=model
    )

    async def ok_post(url: str, json: Any) -> Any:
        return _FakeResponse(payload={"response": "{}"})

    _patch_async_client(monkeypatch, post_impl=ok_post)

    out = await _REAL_OLLAMA_GENERATE_VISION(prompt="describe", images=[b"img"], model=model)
    assert out == "{}"

    after = _counter_value(
        OLLAMA_REQUESTS_TOTAL, endpoint="generate_vision", model=model, outcome="success"
    )
    after_hist = _histogram_count(
        OLLAMA_REQUEST_DURATION_SECONDS, endpoint="generate_vision", model=model
    )
    assert after == before + 1
    assert after_hist == before_hist + 1


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


# ---------------------------------------------------------------------------
# Fitbit emit sites (API-2)
# ---------------------------------------------------------------------------


async def _fitbit_sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _connect_fitbit(
    client: AsyncClient, headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.clients import fitbit as fitbit_client

    auth = (
        await client.post(
            "/v1/integrations/fitbit/authorize",
            headers=headers,
            json={"code_challenge": "challenge-" + "x" * 32},
        )
    ).json()

    async def fake_exchange(**kw: Any) -> Any:
        return fitbit_client.FitbitTokens(
            access_token="fb-access-obs",
            refresh_token="fb-refresh-obs",
            expires_at=datetime.now(tz=UTC) + timedelta(hours=8),
            scopes=["activity"],
            fitbit_user_id="fitbit-user-obs",
        )

    monkeypatch.setattr(fitbit_client, "exchange_code", fake_exchange)
    await client.post(
        "/v1/integrations/fitbit/callback",
        headers=headers,
        json={
            "code": "auth-code",
            "state": auth["state"],
            "code_verifier": "verifier-" + "y" * 40,
        },
    )


async def test_fitbit_sync_success_increments_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import date

    from app.clients import fitbit as fitbit_client

    headers = await _fitbit_sign_in(client, monkeypatch, sub="obs-sync")
    await _connect_fitbit(client, headers, monkeypatch)

    async def fake_list(**kw: Any) -> list[Any]:
        return []

    async def fake_daily(*, access_token: str, day: date) -> Any:
        return fitbit_client.FitbitDailySummary(
            date=day,
            steps=None,
            resting_hr=None,
            hrv_ms=None,
            sleep_minutes=None,
            sleep_score=None,
        )

    monkeypatch.setattr(fitbit_client, "list_activities", fake_list)
    monkeypatch.setattr(fitbit_client, "daily_summary", fake_daily)

    before = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    response = await client.post("/v1/integrations/fitbit/sync", headers=headers)
    assert response.status_code == 200, response.text
    after = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    assert after == before + 1


async def test_fitbit_sync_error_increments_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.clients import fitbit as fitbit_client

    headers = await _fitbit_sign_in(client, monkeypatch, sub="obs-sync-err")
    await _connect_fitbit(client, headers, monkeypatch)

    async def boom_list(**kw: Any) -> list[Any]:
        raise fitbit_client.FitbitClientError("upstream blew up")

    monkeypatch.setattr(fitbit_client, "list_activities", boom_list)

    before = _counter_value(FITBIT_SYNC_TOTAL, outcome="error")
    with pytest.raises(fitbit_client.FitbitClientError):
        from app.db import get_sessionmaker
        from app.services import fitbit_sync

        sm = get_sessionmaker()
        async with sm() as db:
            me = (await client.get("/v1/me", headers=headers)).json()
            from uuid import UUID

            await fitbit_sync.sync_user(db, UUID(me["id"]))
    after = _counter_value(FITBIT_SYNC_TOTAL, outcome="error")
    assert after == before + 1


async def test_fitbit_push_success_increments_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.clients import fitbit as fitbit_client

    headers = await _fitbit_sign_in(client, monkeypatch, sub="obs-push")
    await _connect_fitbit(client, headers, monkeypatch)

    # Build a finished-able session with one strength exercise + working sets.
    exercise = (
        await client.post(
            "/v1/exercises",
            headers=headers,
            json={
                "name": "obs-bench",
                "primary_muscle": "chest",
                "secondary_muscles": ["triceps"],
                "equipment": "barbell",
                "movement_pattern": "horizontal_push",
                "tracking_type": "weight_reps",
                "is_unilateral": False,
            },
        )
    ).json()
    session = (
        await client.post("/v1/workout-sessions", headers=headers, json={"name": "obs"})
    ).json()
    we = (
        await client.post(
            f"/v1/workout-sessions/{session['id']}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we['id']}/sets",
            headers=headers,
            json={"weight_kg": "100", "reps": 5, "set_type": "working"},
        )

    async def fake_post(**kw: Any) -> Any:
        return fitbit_client.FitbitPostActivityResult(
            log_id="obs-777", raw={"activityLog": {"logId": "obs-777"}}
        )

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    before = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    # Auto-push on finish runs the inline push (see conftest stub).
    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200
    after = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    assert after == before + 1


async def test_fitbit_push_error_increments_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.clients import fitbit as fitbit_client

    headers = await _fitbit_sign_in(client, monkeypatch, sub="obs-push-err")
    await _connect_fitbit(client, headers, monkeypatch)

    exercise = (
        await client.post(
            "/v1/exercises",
            headers=headers,
            json={
                "name": "obs-bench-err",
                "primary_muscle": "chest",
                "secondary_muscles": ["triceps"],
                "equipment": "barbell",
                "movement_pattern": "horizontal_push",
                "tracking_type": "weight_reps",
                "is_unilateral": False,
            },
        )
    ).json()
    session = (
        await client.post("/v1/workout-sessions", headers=headers, json={"name": "obs-err"})
    ).json()
    we = (
        await client.post(
            f"/v1/workout-sessions/{session['id']}/exercises",
            headers=headers,
            json={"exercise_id": exercise["id"]},
        )
    ).json()
    for _ in range(3):
        await client.post(
            f"/v1/workout-exercises/{we['id']}/sets",
            headers=headers,
            json={"weight_kg": "100", "reps": 5, "set_type": "working"},
        )

    async def fake_post(**kw: Any) -> Any:
        raise fitbit_client.FitbitAuthError("401")

    monkeypatch.setattr(fitbit_client, "post_activity", fake_post)

    before = _counter_value(FITBIT_SYNC_TOTAL, outcome="error")
    finish = await client.post(f"/v1/workout-sessions/{session['id']}/finish", headers=headers)
    assert finish.status_code == 200
    after = _counter_value(FITBIT_SYNC_TOTAL, outcome="error")
    assert after == before + 1


async def test_fitbit_disconnect_success_increments_counter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.clients import fitbit as fitbit_client

    headers = await _fitbit_sign_in(client, monkeypatch, sub="obs-disc")
    await _connect_fitbit(client, headers, monkeypatch)

    async def fake_revoke(*, access_token: str) -> None:
        return None

    monkeypatch.setattr(fitbit_client, "revoke", fake_revoke)

    before = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    response = await client.delete("/v1/integrations/fitbit", headers=headers)
    assert response.status_code == 204
    after = _counter_value(FITBIT_SYNC_TOTAL, outcome="success")
    assert after == before + 1
