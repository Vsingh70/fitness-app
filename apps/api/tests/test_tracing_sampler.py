"""Unit tests for the error-aware trace sampler.

These are pure unit tests (no DB / testcontainer needed): they exercise the
sampling decision logic directly against the OTel SDK ``Decision`` enum.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace.sampling import (
    Decision,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)

from app.observability.tracing import (
    ErrorAwareSampler,
    build_error_aware_sampler,
)

# A trace_id that the 0%-ratio baseline sampler will always DROP. Any positive
# trace_id is above the bound when the ratio is 0, so the baseline drops it.
_DROPPED_TRACE_ID = 0x1234_5678_9ABC_DEF0_1234_5678_9ABC_DEF0


def _never_sample() -> Sampler:
    """Sampler whose baseline drops everything (ratio 0)."""
    return build_error_aware_sampler(0.0)


def _always_sample() -> Sampler:
    return build_error_aware_sampler(1.0)


def test_baseline_drops_non_error_span_when_ratio_zero() -> None:
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes={"http.request.method": "GET"},
    )
    assert result.decision is Decision.DROP


def test_error_span_is_forced_sampled_even_when_ratio_would_drop() -> None:
    """The core acceptance test: an erroring span is RECORD_AND_SAMPLE
    despite a 0% baseline ratio that would otherwise drop it."""
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes={"error": True},
    )
    assert result.decision is Decision.RECORD_AND_SAMPLE
    # Attributes must survive the upgrade (the delegate nulls them on DROP).
    assert result.attributes is not None
    assert result.attributes.get("error") is True


def test_otel_status_error_attribute_forces_sample() -> None:
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="db.query",
        attributes={"otel.status_code": "ERROR"},
    )
    assert result.decision is Decision.RECORD_AND_SAMPLE


def test_exception_attributes_force_sample() -> None:
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="task.run",
        attributes={"exception.type": "ValueError"},
    )
    assert result.decision is Decision.RECORD_AND_SAMPLE


@pytest.mark.parametrize(
    ("status_key", "status_value", "expected"),
    [
        ("http.response.status_code", 500, Decision.RECORD_AND_SAMPLE),
        ("http.response.status_code", 503, Decision.RECORD_AND_SAMPLE),
        ("http.status_code", "502", Decision.RECORD_AND_SAMPLE),
        # 4xx is a client error, not forced; baseline (ratio 0) drops it.
        ("http.response.status_code", 404, Decision.DROP),
        ("http.response.status_code", 200, Decision.DROP),
    ],
)
def test_http_status_code_forcing(
    status_key: str, status_value: int | str, expected: Decision
) -> None:
    sampler = _never_sample()
    # Codes may arrive as int or (occasionally) str; both must parse. The
    # parametrize set mixes the two on purpose.
    attributes: dict[str, int | str] = {status_key: status_value}
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes=attributes,
    )
    assert result.decision is expected


def test_no_attributes_falls_through_to_baseline() -> None:
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes=None,
    )
    assert result.decision is Decision.DROP


def test_full_sampling_baseline_keeps_record_and_sample() -> None:
    """When the baseline already samples, the decision passes through."""
    sampler = _always_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes={"http.request.method": "GET"},
    )
    assert result.decision is Decision.RECORD_AND_SAMPLE


def test_get_description_mentions_delegate_and_ratio() -> None:
    sampler = build_error_aware_sampler(0.1)
    desc = sampler.get_description()
    assert "ErrorAwareSampler" in desc
    assert "0.1" in desc
    assert "ParentBased" in desc


def test_wraps_parent_based_ratio_delegate() -> None:
    sampler = build_error_aware_sampler(0.25)
    assert isinstance(sampler, ErrorAwareSampler)
    # The delegate is the parent-based ratio sampler the spec calls for.
    assert isinstance(sampler._delegate, ParentBased)


def test_error_false_attribute_does_not_force_sample() -> None:
    """An explicit error=False must not force sampling."""
    sampler = _never_sample()
    result = sampler.should_sample(
        parent_context=None,
        trace_id=_DROPPED_TRACE_ID,
        name="GET /v1/workouts",
        attributes={"error": False},
    )
    assert result.decision is Decision.DROP


def test_ratio_baseline_uses_trace_id_ratio_under_parent_based() -> None:
    """Sanity check that the delegate is built from TraceIdRatioBased."""
    delegate = ParentBased(TraceIdRatioBased(0.5))
    sampler = ErrorAwareSampler(delegate, ratio=0.5)
    # No error attrs -> identical decision to the delegate for a given id.
    direct = delegate.should_sample(None, _DROPPED_TRACE_ID, "x", attributes=None)
    wrapped = sampler.should_sample(None, _DROPPED_TRACE_ID, "x", attributes=None)
    assert wrapped.decision is direct.decision
