"""OpenTelemetry tracing setup.

If `OTEL_EXPORTER_OTLP_ENDPOINT` is unset, this is a no-op. When set, the
SDK is initialized with an error-aware, parent-based sampler:
- baseline 10% trace_id_ratio sampling (``settings.otel_sample_ratio``)
- any span flagged as an error at start time is force-sampled (100% on
  errors), even when the ratio would otherwise drop it.

Auto-instrumentation: FastAPI request spans, SQLAlchemy queries, outbound
httpx. Spans are exported via the OTLP HTTP exporter (Honeycomb / Tempo).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI

from app.config import get_settings

if TYPE_CHECKING:
    from opentelemetry.context import Context
    from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult
    from opentelemetry.trace import Link, SpanKind
    from opentelemetry.trace.span import TraceState
    from opentelemetry.util.types import Attributes

logger = logging.getLogger(__name__)

# Span attribute keys that, when present/truthy, mean the span represents an
# error and must always be sampled regardless of the baseline ratio. OTel's
# `should_sample` runs at span *start*, so the span status (ERROR) is not yet
# set; error intent is surfaced via these start-time attributes instead.
_ERROR_BOOL_ATTRS = ("error",)
_ERROR_PRESENCE_ATTRS = (
    "exception.type",
    "exception.message",
    "otel.status_code",
)


def _attributes_signal_error(attributes: Attributes) -> bool:
    """Return True when start-time attributes mark the span as an error.

    Covers three signals:
    - an explicit ``error`` boolean (or truthy) attribute,
    - presence of exception attributes (``exception.type`` etc.),
    - an HTTP status code in the 5xx range (server error).
    """
    if not attributes:
        return False

    for key in _ERROR_BOOL_ATTRS:
        if key in attributes and bool(attributes[key]):
            return True

    for key in _ERROR_PRESENCE_ATTRS:
        if attributes.get(key):
            return True

    # An explicit OTel status code attribute set to ERROR.
    if str(attributes.get("otel.status_code", "")).upper() == "ERROR":
        return True

    # HTTP 5xx (and explicit 4xx? -> no, only server errors are forced).
    for key in ("http.response.status_code", "http.status_code"):
        raw = attributes.get(key)
        if raw is None:
            continue
        try:
            if int(raw) >= 500:  # type: ignore[arg-type]
                return True
        except (TypeError, ValueError):
            continue

    return False


def build_error_aware_sampler(ratio: float) -> Sampler:
    """Build the production sampler: ratio baseline, 100% on errors.

    Wraps ``ParentBased(TraceIdRatioBased(ratio))`` and overrides its
    decision to ``RECORD_AND_SAMPLE`` whenever a span carries an
    error-indicating attribute at start time.
    """
    from opentelemetry.sdk.trace.sampling import (
        ParentBased,
        TraceIdRatioBased,
    )

    # ErrorAwareSampler structurally implements the OTel Sampler protocol;
    # cast so callers see the public Sampler type without importing the SDK.
    return cast(
        "Sampler",
        ErrorAwareSampler(ParentBased(TraceIdRatioBased(ratio)), ratio=ratio),
    )


class ErrorAwareSampler:
    """Sampler that force-samples error spans on top of a delegate.

    Implements the OTel ``Sampler`` protocol. For non-error spans the
    decision is taken verbatim from the wrapped ``delegate`` (the baseline
    parent-based ratio sampler). For spans whose start-time attributes
    signal an error, the decision is upgraded to ``RECORD_AND_SAMPLE`` so
    errors are captured at 100% even when the ratio would drop them.
    """

    def __init__(self, delegate: Sampler, *, ratio: float) -> None:
        self._delegate = delegate
        self._ratio = ratio

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        from opentelemetry.sdk.trace.sampling import Decision, SamplingResult

        base = self._delegate.should_sample(
            parent_context,
            trace_id,
            name,
            kind=kind,
            attributes=attributes,
            links=links,
            trace_state=trace_state,
        )
        if base.decision is Decision.RECORD_AND_SAMPLE:
            return base

        if _attributes_signal_error(attributes):
            # Preserve attributes (delegate nulls them when it drops) and
            # carry through the trace_state so downstream propagation works.
            return SamplingResult(
                Decision.RECORD_AND_SAMPLE,
                attributes,
                base.trace_state,
            )

        return base

    def get_description(self) -> str:
        return (
            f"ErrorAwareSampler{{delegate={self._delegate.get_description()},ratio={self._ratio}}}"
        )


def configure_tracing(app: FastAPI) -> None:
    """Idempotent. Returns early when the OTLP endpoint isn't configured."""
    settings = get_settings()
    endpoint = settings.otel_exporter_otlp_endpoint
    if not endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.git_sha,
            "deployment.environment": settings.environment,
        }
    )
    sampler = build_error_aware_sampler(settings.otel_sample_ratio)
    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app, excluded_urls="/metrics,/v1/health,/v1/health/ready,/v1/health/live"
    )
    SQLAlchemyInstrumentor().instrument(enable_commenter=True, commenter_options={})
    HTTPXClientInstrumentor().instrument()
    logger.info("otel_tracing_enabled", extra={"endpoint": endpoint})
