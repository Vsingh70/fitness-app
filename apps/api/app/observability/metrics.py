"""Prometheus metrics surface.

- A single `CollectorRegistry` is used so tests can scrape it without
  importing the global default registry.
- Per-request counters/histograms registered via FastAPI middleware in
  `app/middleware/metrics.py`.
- Custom app-level metrics (Ollama latency) are registered here so callers
  don't import prometheus_client directly.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests by method, route, and status class.",
    labelnames=("method", "route", "status_class"),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, bucketed for p50/p95/p99.",
    labelnames=("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

OLLAMA_REQUEST_DURATION_SECONDS = Histogram(
    "ollama_request_duration_seconds",
    "Ollama call latency in seconds by model + endpoint.",
    labelnames=("endpoint", "model"),
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

OLLAMA_REQUESTS_TOTAL = Counter(
    "ollama_requests_total",
    "Ollama calls by outcome.",
    labelnames=("endpoint", "model", "outcome"),
    registry=REGISTRY,
)

SOFT_DELETE_PURGED_TOTAL = Counter(
    "soft_delete_purged_total",
    "Rows hard-deleted by the nightly soft-delete cleanup job, labeled by table.",
    labelnames=("table",),
    registry=REGISTRY,
)


def status_class(status_code: int) -> str:
    """1xx..5xx for low-cardinality status labeling."""
    return f"{status_code // 100}xx"
