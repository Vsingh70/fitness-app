"""Helpers for custom OpenTelemetry spans.

All of this is a safe no-op when no SDK TracerProvider is configured (i.e.
when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset): ``trace.get_tracer`` returns a
proxy/no-op tracer, ``start_as_current_span`` yields a non-recording span, and
``set_attribute`` is a cheap no-op. None of these import the SDK, so the
no-op path never pulls in the exporter.

Privacy: user ids are NEVER attached raw. ``hash_user_id`` runs sha256 and
truncates to 16 hex chars (enough to correlate, cheap to store, not reversible
to the UUID). ``request_id`` is read from the structlog contextvars that the
request-logging middleware binds, when present.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import Span, Tracer

_TRACER_NAME = "app.custom"
_USER_ID_HASH_LEN = 16


def get_tracer() -> Tracer:
    """Return a tracer. Safe even with no SDK provider configured."""
    return trace.get_tracer(_TRACER_NAME)


def hash_user_id(user_id: Any | None) -> str | None:
    """sha256-hash a user id to a short hex digest. Never returns the raw id."""
    if user_id is None:
        return None
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:_USER_ID_HASH_LEN]


def current_request_id() -> str | None:
    """Read request_id bound by the request-logging middleware, if any."""
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return str(request_id) if request_id else None


def _apply_attributes(
    span: Span,
    *,
    user_id: Any | None,
    request_id: str | None,
    extra: Mapping[str, Any] | None,
) -> None:
    if not span.is_recording():
        return
    hashed = hash_user_id(user_id)
    if hashed is not None:
        span.set_attribute("user_id.hashed", hashed)
    rid = request_id or current_request_id()
    if rid is not None:
        span.set_attribute("request_id", rid)
    if extra:
        for key, value in extra.items():
            if value is not None:
                span.set_attribute(key, value)


@contextmanager
def traced_span(
    name: str,
    *,
    user_id: Any | None = None,
    request_id: str | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Span]:
    """Start a span with the given name and standard attributes.

    ``user_id`` is hashed (never stored raw). ``request_id`` falls back to the
    middleware-bound contextvar. No-op when no provider is configured.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        _apply_attributes(span, user_id=user_id, request_id=request_id, extra=attributes)
        yield span


def traced_arq_job[T](
    func: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    """Wrap an ARQ job coroutine in a ``arq.<job_name>`` span.

    If the job takes a ``user_id`` parameter (positionally or by keyword), its
    value is hashed onto the span. No-op when no provider is configured.
    """
    span_name = f"arq.{func.__name__}"
    signature = inspect.signature(func)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        user_id: Any | None = None
        try:
            bound = signature.bind(*args, **kwargs)
            user_id = bound.arguments.get("user_id")
        except TypeError:
            user_id = kwargs.get("user_id")
        with traced_span(span_name, user_id=user_id):
            return await func(*args, **kwargs)

    return wrapper
