# 04.03 Mesocycles and deloads

## Context

Programs are organized into mesocycles (typically 4 to 8 weeks of progressive overload followed by 1 deload week). The engine needs to track mesocycle progress and apply a deload automatically when due, or when fatigue signals demand it.

## Goal

Mesocycle tracking, automatic deload weeks within programs, and fatigue-driven deload recommendations.

## Schema

Add to `programs`:
- `mesocycle_length_weeks` int default 4
- `auto_deload` boolean default true

`scheduled_workouts.mesocycle_week` is computed at activation time:
- Week 1..N are progression weeks.
- Week N+1 is a deload week (`is_deload = true`).

During a deload week:
- Volume reduced to 60% of working sets.
- Intensity reduced to 80% of last working weight.
- RPE targets capped at 6.5.

## Fatigue signals (heuristic)

Fatigue accumulator updated per session:
- +1 per session where average RPE exceeded the target range.
- +0.5 per failed working set.
- +1 if Fitbit `daily_metrics.resting_hr` is more than 5 BPM above the user's 14-day average for 3+ days (when Fitbit is connected; otherwise this signal is skipped).
- -1 per planned rest day.

If the rolling 7-day fatigue score crosses a threshold (default 6), insert an `analytics_insights` row of kind `stagnation` with severity `action` recommending a deload now even if not scheduled.

## Endpoints

- `GET /v1/programs/{id}/mesocycle` returns current week, total weeks in current meso, and whether next week is a deload.
- `POST /v1/programs/{id}/trigger-deload` user-initiated deload. Shifts the current week's scheduled workouts to deload behavior and reschedules subsequent weeks.

## Implementation

Service `apps/api/app/services/progression/mesocycle.py`:
- `compute_mesocycle_position(program, scheduled_for)` -> `(meso_index, week_in_meso, is_deload)`.
- `apply_deload_to_session(session_targets)` -> reduced targets.

The orchestrator from 04.01/04.02 checks `scheduled_workout.is_deload` before applying progression. On a deload, recommendations are "hold weight, reduce volume to 60%, reduce intensity to 80%".

## Deliverables

1. Schema changes + migration.
2. Mesocycle position computation.
3. Fatigue accumulator updated by `finalize_session` and a nightly job that pulls in Fitbit signals when available.
4. Deload trigger API.
5. UI hooks: badge on the calendar for deload weeks. Insight card on Today when an action-level deload is recommended.
6. Tests:
   - Mesocycle position over an 8-week program.
   - Deload week applies reduced targets.
   - High-fatigue mock produces a deload recommendation.

## Acceptance criteria

- Activating an 8-week program with default meso length produces weeks 1-4 normal, week 5 deload, weeks 6-8 normal.
- Manually triggering a deload re-tunes the current week's scheduled workouts.
- Fatigue-driven recommendation appears in `analytics_insights` and on the Today screen.

## Dependencies

- `04.01`, `04.02`
- (optional fatigue signal: `07.x daily_metrics` from Fitbit; gracefully degrade if absent)

## Out of scope

- Macrocycles spanning multiple mesocycles (not modeled in v1).
