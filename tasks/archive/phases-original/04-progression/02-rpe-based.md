# 04.02 RPE-based progression

## Context

For more advanced lifters, RPE (Rate of Perceived Exertion) is a more accurate signal than fixed rep targets. The engine uses the RPE of the top working set to decide whether to push, hold, or back off.

## Goal

RPE-based strategy implemented and orchestrated alongside the linear/double-progression strategies.

## Rules

- Each exercise has a target RPE range, e.g. `[7, 8]`.
- After a session:
  - If average top-set RPE was below the range, increase weight by one increment (default 2.5%).
  - If within range, follow the program: add reps if rep target not met, else add weight when at top of rep range.
  - If above the range by 0.5 to 1.0, hold weight, focus on reps.
  - If above the range by more than 1.0, back off 5% next session.
- Track `consecutive_above_range` to detect overreach. After 3 consecutive sessions above range, recommend a deload.

## Use e1RM as a sanity check

Compute estimated 1RM from each set. If next-session recommendation would imply an e1RM jump greater than 2.5% week-over-week, cap the increase. Prevents the engine from getting carried away on a great day.

## Implementation

Pure function `rpe_progression(input: RPEInput) -> ProgressionDecision`.

Inputs:
- `last_session_sets: list[Set]` (working sets only)
- `target_rpe_low: float`
- `target_rpe_high: float`
- `target_reps_low: int`
- `target_reps_high: int | None`
- `current_weight_kg: float`
- `consecutive_above: int`
- `recent_e1rm: list[float]` (last 4 sessions for the sanity check)

## Deliverables

1. `rpe_progression` function with tests across many scenarios.
2. Wire into the orchestrator from 04.01: pick strategy by `program_day_exercise.progression_strategy`.
3. Tests including:
   - User crushes the prescribed sets at RPE 6 -> recommend bigger jump.
   - User grinds at RPE 9.5 -> back off.
   - 3 sessions in a row above range -> deload recommendation.
   - e1RM sanity cap kicks in when raw rule says jump too much.

## Acceptance criteria

- Function behavior matches an explicit rule table documented in the source file.
- Orchestrator dispatches correctly based on strategy enum.

## Dependencies

- `04.01 Linear and double progression`

## Out of scope

- Mesocycles and deloads as program-level concepts (next task).
