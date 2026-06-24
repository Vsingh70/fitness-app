# 05.01 Per-muscle volume and weekly rollups

## Context

Foundation for analytics. We need accurate weekly volume per muscle, with primary/secondary weighting, computed efficiently.

Reference: `00-overview/data-model.md` (muscle_volume_weekly).

## Goal

A nightly job that recomputes weekly volumes per user per muscle, plus on-demand recompute when sessions change.

## Definitions

For a single set on an exercise:
- Primary muscle contribution: 1.0 working set (only `set_type = working`).
- Secondary muscles: 0.5 working sets each.
- Tonnage for the set: `weight_kg * reps` when both present. Bodyweight-only sets contribute reps weighted by the user's bodyweight (use `workout_sessions.bodyweight_kg` if present; else the latest known; else null/skip tonnage).

Weekly rollup keyed by ISO year + ISO week.

## Job

`apps/api/app/workers/analytics_rollup.py`:

```python
async def rollup_user_week(user_id: UUID, iso_year: int, iso_week: int) -> None: ...
async def rollup_all_users_yesterday() -> None: ...
```

`rollup_user_week` deletes existing rows for that user+week, then re-inserts.

`rollup_all_users_yesterday` runs nightly at 02:00 UTC and rolls up the week containing yesterday for every user with activity that week.

## Reactive recompute

When a session is finished or edited, enqueue `rollup_user_week` for the affected week. Use job dedup (same user+week within 60s collapse to one execution).

## Endpoints

- `GET /v1/analytics/volume`
  - Query: `from`, `to`, `granularity` (`week` default; `month` aggregates weeks).
  - Returns per-muscle series: `{ muscle, points: [{ iso_year, iso_week, working_sets, tonnage_kg, average_rir }] }`.
- `GET /v1/analytics/volume/current-week` quick summary for the Today screen.

## Web UI

New section on `/insights`:
- Stacked area chart of weekly sets per muscle group.
- Toggleable: total volume (kg) over time.
- Per-muscle drill-down opens a page with exercise breakdown for that muscle in the selected window.

## Deliverables

1. SQL or SQLAlchemy implementation of the rollup. Prefer a single SQL statement using `unnest` on `secondary_muscles` for accuracy.
2. Nightly scheduler hook in ARQ.
3. Reactive trigger in `finalize_session` and session edit endpoints.
4. API endpoints.
5. Web UI components.
6. Tests:
   - Seeded fixture of 4 weeks of sessions, rollup matches hand-counted values.
   - Editing a session triggers recompute; the row updates.

## Acceptance criteria

- Rollup of a single user-week completes in under 500ms on realistic data.
- Numbers in the UI match a hand check from the session log.

## Dependencies

- `02.01 Workout sessions API`
- `01.04 Exercise library` (for primary/secondary muscles)

## Out of scope

- Estimated MAV/MRV (handled in 05.02).
