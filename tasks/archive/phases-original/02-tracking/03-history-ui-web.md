# 02.03 History and exercise detail (web)

## Context

After tracking, users need to look back. Sessions list, calendar view, and per-exercise history.

## Goal

History UI surfaces. Read-only here; edits happen on the in-progress screen.

## Screens

### Sessions list
Route: `/workouts`. Infinite scroll, grouped by week. Each row shows date, name, duration, volume, exercise count, and a PR badge if any.

### Calendar
Route: `/workouts/calendar`. Month grid with a dot per day that had a session. Tap a day to open the session.

### Session detail (read-only)
Route: `/workouts/[id]` when `ended_at` is set. Same layout as the in-progress screen but everything is read-only; an "Edit" toggle flips it editable (PATCH endpoints).

### Exercise history
Route: `/exercises/[id]`. Shows:
- Best estimated 1RM over time (line chart).
- Volume over time (bar chart).
- All sets ever logged (table, paginated).
- Filter: last 4w / 12w / 6mo / 1y / all.
- Comparison option: pick another exercise to overlay e1RM.

## Charts

Use `recharts` on web. Conform to design system colors. Tooltips show date + value + a thumbnail of the set context.

## Deliverables

1. Routes and components.
2. Reusable `<TrendChart>` component used in this task and later analytics tasks.
3. Tests for filtering ranges and e1RM math.

## Acceptance criteria

- Exercise history loads under 500ms for a user with 2 years of data.
- Calendar correctly handles timezone boundaries (use the user's stored timezone).

## Dependencies

- `02.01 Workout sessions API`
- `02.02 Workout logging UI (web)` (for shared components)

## Out of scope

- Export to CSV (later).
