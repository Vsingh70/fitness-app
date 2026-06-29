"""Pure-function tests for the exercise seed mapping logic (no DB required)."""

from __future__ import annotations

from app.models.enums import MovementPattern, TrackingType
from scripts.seed_exercises import _build_exercise_row, infer_movement_pattern

# ---------------------------------------------------------------------------
# infer_movement_pattern
# ---------------------------------------------------------------------------


def test_infer_movement_pattern_stretching_returns_mobility() -> None:
    assert infer_movement_pattern("90/90 Hamstring", "stretching") == MovementPattern.mobility


def test_infer_movement_pattern_plyometrics_returns_plyometric() -> None:
    assert infer_movement_pattern("Bench Jump", "plyometrics") == MovementPattern.plyometric


def test_infer_movement_pattern_cardio_unchanged() -> None:
    assert infer_movement_pattern("Running", "cardio") == MovementPattern.cardio


def test_infer_movement_pattern_strength_squat() -> None:
    assert infer_movement_pattern("Barbell Back Squat", "strength") == MovementPattern.squat


def test_infer_movement_pattern_strength_fallback_isolation() -> None:
    assert infer_movement_pattern("Bicep Curl", "strength") == MovementPattern.isolation


# ---------------------------------------------------------------------------
# _build_exercise_row — stretching category
# ---------------------------------------------------------------------------

_STRETCHING_ENTRY = {
    "name": "90/90 Hamstring",
    "force": "push",
    "level": "beginner",
    "mechanic": None,
    "equipment": "body only",
    "primaryMuscles": ["hamstrings"],
    "secondaryMuscles": ["calves"],
    "instructions": ["Lie on your back.", "Extend your leg straight into the air."],
    "category": "stretching",
    "id": "90_90_Hamstring",
}

_STRETCHING_NO_EQUIPMENT = {
    "name": "Adductor/Groin",
    "force": "static",
    "level": "intermediate",
    "mechanic": None,
    "equipment": None,
    "primaryMuscles": ["adductors"],
    "secondaryMuscles": [],
    "instructions": ["Lie on your back with your feet raised."],
    "category": "stretching",
    "id": "Adductor_Groin",
}


def test_build_row_stretching_is_not_dropped() -> None:
    row = _build_exercise_row(_STRETCHING_ENTRY)
    assert row is not None


def test_build_row_stretching_movement_pattern_is_mobility() -> None:
    row = _build_exercise_row(_STRETCHING_ENTRY)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.mobility.value


def test_build_row_stretching_tracking_type_is_time_only() -> None:
    row = _build_exercise_row(_STRETCHING_ENTRY)
    assert row is not None
    assert row["tracking_type"] == TrackingType.time_only.value


def test_build_row_stretching_no_equipment_defaults_to_bodyweight() -> None:
    """Entries with equipment=None must not be dropped; they default to bodyweight."""
    row = _build_exercise_row(_STRETCHING_NO_EQUIPMENT)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.mobility.value
    assert row["tracking_type"] == TrackingType.time_only.value


# ---------------------------------------------------------------------------
# _build_exercise_row — plyometrics category
# ---------------------------------------------------------------------------

_PLYOMETRIC_BODY_ONLY = {
    "name": "Bench Jump",
    "force": "push",
    "level": "intermediate",
    "mechanic": "compound",
    "equipment": "body only",
    "primaryMuscles": ["quadriceps"],
    "secondaryMuscles": ["calves", "glutes", "hamstrings"],
    "instructions": ["Begin with a box or bench 1-2 feet in front of you."],
    "category": "plyometrics",
    "id": "Bench_Jump",
}

_PLYOMETRIC_NO_EQUIPMENT = {
    "name": "Alternate Leg Diagonal Bound",
    "force": "push",
    "level": "beginner",
    "mechanic": "compound",
    "equipment": None,
    "primaryMuscles": ["quadriceps"],
    "secondaryMuscles": ["abductors", "calves", "glutes", "hamstrings"],
    "instructions": ["Assume a comfortable stance."],
    "category": "plyometrics",
    "id": "Alternate_Leg_Diagonal_Bound",
}


def test_build_row_plyometrics_is_not_dropped() -> None:
    row = _build_exercise_row(_PLYOMETRIC_BODY_ONLY)
    assert row is not None


def test_build_row_plyometrics_movement_pattern_is_plyometric() -> None:
    row = _build_exercise_row(_PLYOMETRIC_BODY_ONLY)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.plyometric.value


def test_build_row_plyometrics_tracking_type_is_bodyweight_reps() -> None:
    row = _build_exercise_row(_PLYOMETRIC_BODY_ONLY)
    assert row is not None
    assert row["tracking_type"] == TrackingType.bodyweight_reps.value


def test_build_row_plyometrics_no_equipment_not_dropped() -> None:
    """Plyometrics with equipment=None must not be dropped."""
    row = _build_exercise_row(_PLYOMETRIC_NO_EQUIPMENT)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.plyometric.value
    assert row["tracking_type"] == TrackingType.bodyweight_reps.value


# ---------------------------------------------------------------------------
# Regression: existing strength rows still map correctly
# ---------------------------------------------------------------------------

_STRENGTH_BENCH_PRESS = {
    "name": "Barbell Bench Press - Medium Grip",
    "force": "push",
    "level": "beginner",
    "mechanic": "compound",
    "equipment": "barbell",
    "primaryMuscles": ["chest"],
    "secondaryMuscles": ["shoulders", "triceps"],
    "instructions": ["Lie back on a flat bench."],
    "category": "strength",
    "id": "Barbell_Bench_Press_-_Medium_Grip",
}

_STRENGTH_CURL = {
    "name": "Dumbbell Bicep Curl",
    "force": "pull",
    "level": "beginner",
    "mechanic": "isolation",
    "equipment": "dumbbell",
    "primaryMuscles": ["biceps"],
    "secondaryMuscles": [],
    "instructions": ["Stand with a dumbbell in each hand."],
    "category": "strength",
    "id": "Dumbbell_Bicep_Curl",
}


def test_build_row_strength_bench_press_is_horizontal_push() -> None:
    row = _build_exercise_row(_STRENGTH_BENCH_PRESS)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.horizontal_push.value


def test_build_row_strength_curl_is_isolation() -> None:
    row = _build_exercise_row(_STRENGTH_CURL)
    assert row is not None
    assert row["movement_pattern"] == MovementPattern.isolation.value


def test_build_row_strength_curl_tracking_type_is_weight_reps() -> None:
    row = _build_exercise_row(_STRENGTH_CURL)
    assert row is not None
    assert row["tracking_type"] == TrackingType.weight_reps.value
