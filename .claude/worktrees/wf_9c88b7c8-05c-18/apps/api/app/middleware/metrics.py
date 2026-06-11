"""Per-request Prometheus instrumentation.

Bucketed by FastAPI's route path (NOT the raw URL), so cardinality stays
bounded even with UUIDs in the path. Excludes /metrics and /v1/health* so
scrape traffic doesn't pollute the histogram.
"""

from __future__ import annotations

import time
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    status_class,
)

EXCLUDED_PATHS = frozenset({"/metrics", "/v1/health", "/v1/health/ready", "/v1/health/live"})


class PrometheusMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "GET")
        status_code_holder: dict[str, int] = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code_holder["code"] = int(message.get("status", 500))
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            route = _route_template(scope) or path
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(elapsed)
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                route=route,
                status_class=status_class(status_code_holder["code"]),
            ).inc()


def _route_template(scope: Scope) -> str | None:
    """Pull the resolved route template (e.g. `/v1/users/{user_id}`) from
    the ASGI scope. Falls back to the raw path if the router hasn't matched.
    """
    route: Any = scope.get("route")
    if route is None:
        return None
    value = getattr(route, "path", None)
    return value if isinstance(value, str) else None


def _build_response(body: bytes, status_code: int, media_type: str) -> Response:
    return Response(content=body, status_code=status_code, media_type=media_type)


def metrics_response(request: Request, expected_token: str) -> Response:
    """Render the registry as Prometheus text exposition format, gated by
    the static `expected_token` (compared via constant-time strings).
    """
    import hmac

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from app.observability.metrics import REGISTRY

    if not expected_token:
        return _build_response(b"metrics disabled", 404, "text/plain")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return _build_response(b"unauthorized", 401, "text/plain")
    presented = header.removeprefix("Bearer ")
    if not hmac.compare_digest(presented, expected_token):
        return _build_response(b"unauthorized", 401, "text/plain")

    body = generate_latest(REGISTRY)
    return _build_response(body, 200, CONTENT_TYPE_LATEST)
