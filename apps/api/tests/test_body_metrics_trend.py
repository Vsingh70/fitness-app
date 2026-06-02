"""Body-metrics trend endpoint: weekly series + trailing moving average."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from app.services import auth as auth_service
from app.services import body_metrics as svc


async def _sign_in(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, sub: str = "trend-sub"
) -> dict[str, str]:
    async def fake_verify(id_token: str, jwks_override: Any = None) -> Any:
        return auth_service.VerifiedIdentity(sub=sub, email=f"{sub}@example.com")

    monkeypatch.setattr("app.routers.auth.verify_apple_token", fake_verify)
    response = await client.post("/v1/auth/apple", json={"id_token": "stub"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def _log(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    recorded_at: datetime,
    weight_kg: str | None = None,
    body_fat_pct: str | None = None,
    waist_cm: str | None = None,
) -> None:
    payload: dict[str, Any] = {"recorded_at": recorded_at.isoformat()}
    if weight_kg is not None:
        payload["weight_kg"] = weight_kg
    if body_fat_pct is not None:
        payload["body_fat_pct"] = body_fat_pct
    if waist_cm is not None:
        payload["waist_cm"] = waist_cm
    resp = await client.post("/v1/body-metrics", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text


async def test_trend_empty_returns_all_metric_series(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    resp = await client.get("/v1/body-metrics/trend?weeks=6&window=3", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["weeks"] == 6
    assert body["window"] == 3
    metrics = {s["metric"] for s in body["series"]}
    assert metrics == {"weight_kg", "body_fat_pct", "neck_cm", "waist_cm", "hip_cm"}
    weight = next(s for s in body["series"] if s["metric"] == "weight_kg")
    assert len(weight["points"]) == 6
    # No data -> all values/moving averages null.
    assert all(p["value"] is None and p["moving_average"] is None for p in weight["points"])


async def test_trend_weekly_mean_and_moving_average(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _sign_in(client, monkeypatch)
    now = datetime.now(tz=UTC)
    this_monday = _monday(now.date())

    # Week -2: two weigh-ins -> mean 80.0; Week -1: 82.0; this week: 81.0.
    wk2 = datetime.combine(this_monday - timedelta(weeks=2), datetime.min.time(), tzinfo=UTC)
    wk1 = datetime.combine(this_monday - timedelta(weeks=1), datetime.min.time(), tzinfo=UTC)
    wk0 = datetime.combine(this_monday, datetime.min.time(), tzinfo=UTC) + timedelta(hours=8)

    await _log(client, headers, recorded_at=wk2, weight_kg="79.00")
    await _log(client, headers, recorded_at=wk2 + timedelta(days=1), weight_kg="81.00")
    await _log(client, headers, recorded_at=wk1, weight_kg="82.00")
    await _log(client, headers, recorded_at=wk0, weight_kg="81.00")

    resp = await client.get("/v1/body-metrics/trend?weeks=4&window=2", headers=headers)
    assert resp.status_code == 200, resp.text
    weight = next(s for s in resp.json()["series"] if s["metric"] == "weight_kg")
    points = weight["points"]
    assert len(points) == 4

    # Oldest bucket (index 0) is week -3: no data.
    assert points[0]["value"] is None
    assert points[0]["moving_average"] is None

    # Week -2: weekly mean = (79+81)/2 = 80.00; MA over [80] = 80.00.
    assert Decimal(points[1]["value"]) == Decimal("80.00")
    assert Decimal(points[1]["moving_average"]) == Decimal("80.00")

    # Week -1: value 82.00; MA over last 2 observed [80,82] = 81.00.
    assert Decimal(points[2]["value"]) == Decimal("82.00")
    assert Decimal(points[2]["moving_average"]) == Decimal("81.00")

    # This week: value 81.00; MA over last 2 observed [82,81] = 81.50.
    assert Decimal(points[3]["value"]) == Decimal("81.00")
    assert Decimal(points[3]["moving_average"]) == Decimal("81.50")

    # Newest bucket carries the correct ISO week label.
    iso_year, iso_week, _ = this_monday.isocalendar()
    assert points[3]["iso_year"] == iso_year
    assert points[3]["iso_week"] == iso_week
    assert points[3]["week_start"] == this_monday.isoformat()

    # A metric never recorded stays empty.
    bf = next(s for s in resp.json()["series"] if s["metric"] == "body_fat_pct")
    assert all(p["value"] is None for p in bf["points"])


async def test_trend_is_per_user_scoped(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = await _sign_in(client, monkeypatch, sub="trend-a")
    now = datetime.now(tz=UTC)
    await _log(client, headers_a, recorded_at=now, weight_kg="90.00")

    headers_b = await _sign_in(client, monkeypatch, sub="trend-b")
    resp = await client.get("/v1/body-metrics/trend?weeks=4", headers=headers_b)
    weight = next(s for s in resp.json()["series"] if s["metric"] == "weight_kg")
    assert all(p["value"] is None for p in weight["points"])


def test_trend_window_validation() -> None:
    """Service treats the moving-average window as a trailing window over the
    most recent observed weekly means, skipping gap weeks."""
    week_buckets = []
    base = date(2026, 1, 5)  # a Monday
    for offset in range(4):
        monday = base + timedelta(weeks=offset)
        iso_year, iso_week, _ = monday.isocalendar()
        week_buckets.append((iso_year, iso_week, monday))

    weekly_values = {
        base: [Decimal("10")],
        base + timedelta(weeks=2): [Decimal("20")],  # gap at week index 1
        base + timedelta(weeks=3): [Decimal("30")],
    }
    series = svc._build_series(
        "weight_kg",
        week_buckets=week_buckets,
        weekly_values=weekly_values,
        window=2,
    )
    pts = series.points
    assert pts[0].value == Decimal("10.00")
    assert pts[0].moving_average == Decimal("10.00")
    # Gap week: no value, but MA still reflects history so far ([10]).
    assert pts[1].value is None
    assert pts[1].moving_average == Decimal("10.00")
    # Window=2 over observed [10,20] = 15.
    assert pts[2].value == Decimal("20.00")
    assert pts[2].moving_average == Decimal("15.00")
    # Window=2 over observed [20,30] = 25.
    assert pts[3].value == Decimal("30.00")
    assert pts[3].moving_average == Decimal("25.00")
