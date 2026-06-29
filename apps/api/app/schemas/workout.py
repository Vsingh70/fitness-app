from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BlockKind, SegmentKind, SetType, TrackingType

# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class WorkoutSessionCreate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    scheduled_workout_id: UUID | None = None
    started_at: datetime | None = None


class WorkoutSessionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    notes: str | None = None
    bodyweight_kg: Decimal | None = Field(default=None, gt=0, le=Decimal("999.99"))
    perceived_exertion: int | None = Field(default=None, ge=1, le=10)
    started_at: datetime | None = None
    ended_at: datetime | None = None


# ---------------------------------------------------------------------------
# Workout exercises
# ---------------------------------------------------------------------------


class WorkoutExerciseCreate(BaseModel):
    exercise_id: UUID
    position: int | None = Field(default=None, ge=0)
    notes: str | None = None
    # Block grouping: ``working`` blocks count toward volume/PRs; ``warmup`` and
    # ``cooldown`` blocks of varied movements are logged but never counted.
    block_kind: BlockKind = BlockKind.working
    block_label: str | None = Field(default=None, max_length=80)


class WorkoutExerciseUpdate(BaseModel):
    notes: str | None = None
    position: int | None = Field(default=None, ge=0)
    block_kind: BlockKind | None = None
    block_label: str | None = Field(default=None, max_length=80)


class WorkoutExerciseReorder(BaseModel):
    position: int = Field(ge=0)


class WorkoutExerciseSwap(BaseModel):
    """Temporary one-session swap: replace this row's exercise with a substitute
    for this session only, recording ``substituted_for_exercise_id`` (the original)
    so the original pauses (neither progressed nor stalled) and logged sets credit
    the substitute."""

    substitute_exercise_id: UUID


# ---------------------------------------------------------------------------
# Set segments (intra-set sub-bouts: rest-pause/cluster/myo + interval rounds)
# ---------------------------------------------------------------------------


class SetSegmentCreate(BaseModel):
    kind: SegmentKind
    segment_index: int | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0, le=10_000)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=Decimal("9999.99"))
    duration_seconds: int | None = Field(default=None, ge=0, le=86_400)
    distance_meters: Decimal | None = Field(default=None, ge=0, le=Decimal("999999.99"))
    rest_seconds: int | None = Field(default=None, ge=0, le=86_400)


class SetSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    segment_index: int
    kind: SegmentKind
    reps: int | None
    weight_kg: Decimal | None
    duration_seconds: int | None
    distance_meters: Decimal | None
    rest_seconds: int | None


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------


class SetCreate(BaseModel):
    """Fields are all optional at the Pydantic layer because validity depends
    on the parent exercise's `tracking_type`, which the route resolves before
    calling `validate_set_payload`."""

    set_type: SetType = SetType.working
    set_index: int | None = Field(default=None, ge=0)

    weight_kg: Decimal | None = Field(default=None, ge=0, le=Decimal("9999.99"))
    reps: int | None = Field(default=None, ge=0, le=10_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=86_400)
    distance_meters: Decimal | None = Field(default=None, ge=0, le=Decimal("999999.99"))
    rpe: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    rir: int | None = Field(default=None, ge=0, le=20)
    notes: str | None = None

    # Interval/HIIT round count (``set_type=interval``); one round is described
    # by the set's ``work``/``rest`` segments.
    rounds: int | None = Field(default=None, ge=1, le=1000)
    # Structured-work sub-bouts: rest-pause/cluster/myo ``mini_set`` segments or
    # interval ``work``/``rest`` segments. A straight set has none.
    segments: list[SetSegmentCreate] = Field(default_factory=list)


class SetUpdate(BaseModel):
    set_type: SetType | None = None
    weight_kg: Decimal | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: Decimal | None = Field(default=None, ge=0)
    rpe: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    rir: int | None = Field(default=None, ge=0, le=20)
    notes: str | None = None
    rounds: int | None = Field(default=None, ge=1, le=1000)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class SetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    set_index: int
    set_type: SetType
    weight_kg: Decimal | None
    reps: int | None
    duration_seconds: int | None
    distance_meters: Decimal | None
    rpe: Decimal | None
    rir: int | None
    is_pr: bool
    notes: str | None
    rounds: int | None
    segments: list[SetSegmentResponse]


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    exercise_name: str
    tracking_type: TrackingType
    position: int
    notes: str | None
    block_kind: BlockKind
    block_label: str | None
    substituted_for_exercise_id: UUID | None
    sets: list[SetResponse]


class WorkoutSessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    started_at: datetime
    ended_at: datetime | None
    perceived_exertion: int | None
    bodyweight_kg: Decimal | None


class WorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    scheduled_workout_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    bodyweight_kg: Decimal | None
    perceived_exertion: int | None
    workout_exercises: list[WorkoutExerciseResponse]


class WorkoutSessionList(BaseModel):
    items: list[WorkoutSessionListItem]
    next_cursor: str | None


# ---------------------------------------------------------------------------
# Per-tracking-type validation
# ---------------------------------------------------------------------------


_REQUIRED: dict[TrackingType, set[str]] = {
    TrackingType.weight_reps: {"weight_kg", "reps"},
    TrackingType.bodyweight_reps: {"reps"},
    TrackingType.weighted_bodyweight: {"weight_kg", "reps"},
    TrackingType.time_only: {"duration_seconds"},
    TrackingType.weight_time: {"weight_kg", "duration_seconds"},
    TrackingType.distance_time: {"distance_meters", "duration_seconds"},
    TrackingType.weight_reps_distance: {"weight_kg", "reps", "distance_meters"},
    TrackingType.distance_time_pace: {"distance_meters", "duration_seconds"},
    TrackingType.cardio_machine: {"duration_seconds"},
}

# Fields that may be present for a given tracking type (required + optional).
_ALLOWED: dict[TrackingType, set[str]] = {
    TrackingType.weight_reps: {"weight_kg", "reps"},
    TrackingType.bodyweight_reps: {"reps", "weight_kg"},
    TrackingType.weighted_bodyweight: {"weight_kg", "reps"},
    TrackingType.time_only: {"duration_seconds"},
    TrackingType.weight_time: {"weight_kg", "duration_seconds"},
    TrackingType.distance_time: {"distance_meters", "duration_seconds"},
    TrackingType.weight_reps_distance: {"weight_kg", "reps", "distance_meters"},
    TrackingType.distance_time_pace: {"distance_meters", "duration_seconds"},
    TrackingType.cardio_machine: {"duration_seconds", "distance_meters"},
}

# Fields rpe/rir/notes/set_type/set_index are always permitted.
_UNIVERSAL_FIELDS = {"set_type", "set_index", "rpe", "rir", "notes"}

# Fields that carry a measurement (subject to per-tracking-type rules).
_MEASUREMENT_FIELDS = {"weight_kg", "reps", "duration_seconds", "distance_meters"}


def validate_set_payload(payload: SetCreate | SetUpdate, tracking_type: TrackingType) -> None:
    """Raise ValueError listing field problems for the given tracking_type.

    For SetCreate: missing required fields and unexpected measurement fields both fail.
    For SetUpdate: only unexpected measurement fields fail (partial update).

    Structured-work sets (rest-pause/cluster/myo/interval) carry their values in
    ``set_segments`` rather than on the set row, so the top-level required-field
    check is skipped when the create payload includes segments. Any top-level
    measurement that *is* provided still has to match the tracking_type.
    """
    provided = payload.model_dump(exclude_unset=True, exclude_none=True)
    measurement_provided = {k for k in provided if k in _MEASUREMENT_FIELDS}

    allowed = _ALLOWED[tracking_type]
    unexpected = measurement_provided - allowed
    if unexpected:
        raise ValueError(
            f"Fields {sorted(unexpected)} not valid for tracking_type={tracking_type.value}"
        )

    has_segments = isinstance(payload, SetCreate) and bool(payload.segments)
    if isinstance(payload, SetCreate) and not has_segments:
        required = _REQUIRED[tracking_type]
        missing = required - measurement_provided
        if missing:
            raise ValueError(
                f"Missing required fields {sorted(missing)} for tracking_type={tracking_type.value}"
            )
