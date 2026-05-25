# 04.01 Linear and double progression

## Context

The simplest progression strategies. After every completed session, the engine decides what to recommend for the next time the user trains that exercise.

Reference: `00-overview/data-model.md` (exercise_progression, recommendations).

## Goal

Implement linear and double-progression strategies as pure functions, plus the orchestration that runs them after `finalize_session`.

## Definitions

### Linear progression
- Used for compounds in beginner programs (e.g. Starting Strength).
- After a successful session at the prescribed reps for all working sets, add a fixed increment (default 2.5 kg for upper, 5 kg for lower; configurable per exercise).
- After 1 failed session, repeat the weight.
- After 2 consecutive failures, deload 10%.
- "Success" = hitting the target rep range on all working sets (warmups, drop sets, etc. excluded).

### Double progression
- Target a rep range like 8 to 12.
- If all working sets hit the top of the range, increase weight by the increment and reset reps to the bottom of the range.
- Otherwise, try to add one rep to the lowest-rep set next time.
- Failure = reps below the bottom of the range on any working set.
- After 2 consecutive failures, deload 5%.

## Implementation

Pure functions in `apps/api/app/services/progression/`:

```python
@dataclass
class LinearInput:
    last_session_sets: list[Set]
    target_reps: int
    increment_kg: float
    current_weight_kg: float
    consecutive_failures: int

@dataclass
class ProgressionDecision:
    next_weight_kg: float
    next_reps_low: int
    next_reps_high: int | None
    is_deload: bool
    rationale_key: str  # template key, filled in by LLM later

def linear_progression(input: LinearInput) -> ProgressionDecision: ...
def double_progression(input: DoubleInput) -> ProgressionDecision: ...
```

Pure, no DB access. Tested heavily with table tests.

## Orchestration

After `finalize_session` runs PR detection:

1. For each `workout_exercise` in the session, look up the `program_day_exercise` (if scheduled). If none, the session was free-style; skip.
2. Read `progression_strategy` from the program day exercise.
3. Read `exercise_progression` for the user+exercise (rolling state).
4. Call the appropriate strategy function.
5. Update `exercise_progression`.
6. Write a row to `recommendations` for the next scheduled workout that contains this exercise.

## Endpoints

- `GET /v1/recommendations` returns unconsumed recommendations for the user.
- `GET /v1/scheduled-workouts/{id}/recommendations` returns recommendations attached to a specific upcoming scheduled workout.
- `POST /v1/recommendations/{id}/consume` marks consumed (called when the user starts the workout).
- `POST /v1/recommendations/{id}/dismiss` user explicitly rejected the rec.

## Deliverables

1. `linear_progression` and `double_progression` functions with tests covering: success, single fail, double fail, deload.
2. Orchestration function called from `finalize_session`.
3. Recommendation API endpoints.
4. Tests covering the orchestration: simulate a 4-week mock log, verify the right weights flow.

## Acceptance criteria

- Mock 4-session linear progression on bench press matches a hand-computed expected sequence.
- Mock double progression that hits the top of the range advances weight and resets reps.
- Two consecutive failures trigger a deload exactly once.

## Dependencies

- `02.01 Workout sessions API`
- `03.01 Program templates`

## Out of scope

- RPE-based and mesocycle progression (next task).
- LLM-generated explanation strings (task 04.04).
