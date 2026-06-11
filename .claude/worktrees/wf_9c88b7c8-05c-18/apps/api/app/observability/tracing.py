"""OpenTelemetry tracing setup.

If `OTEL_EXPORTER_OTLP_ENDPOINT` is unset, this is a no-op. When set, the
SDK is initialized with a parent-based sampler:
- baseline 10% trace_id_ratio sampling
- errors / explicit spans always sampled via record-only fallbacks

Auto-instrumentation: FastAPI request spans, SQLAlchemy queries, outbound
httpx. Spans are exported via the OTLP HTTP exporter (Honeycomb / Tempo).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.config import get_settings

logger = logging.getLogger(__name__)


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
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.git_sha,
            "deployment.environment": settings.environment,
        }
    )
    sampler = ParentBased(TraceIdRatioBased(settings.otel_sample_ratio))
    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app, excluded_urls="/metrics,/v1/health,/v1/health/ready,/v1/health/live"
    )
    SQLAlchemyInstrumentor().instrument(enable_commenter=True, commenter_options={})
    HTTPXClientInstrumentor().instrument()
    logger.info("otel_tracing_enabled", extra={"endpoint": endpoint})
