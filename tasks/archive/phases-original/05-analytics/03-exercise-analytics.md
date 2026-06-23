# 05.03 Exercise-level progression analytics

## Context

The user wants to see, per exercise: how have I progressed, where am I plateauing, what's my predicted next session, are there variants I should swap in.

## Goal

Deep-dive analytics surface for a single exercise.

## Endpoints

- `GET /v1/analytics/exercises/{id}`
  - Query: `window` (default `12w`).
  - Returns:
    - e1RM time series.
    - Volume time series.
    - Average RPE time series.
    - Set-by-set scatter (weight vs reps, colored by date).
    - Recent PRs (date, type, value).
    - Predicted next session targets (pulls from `exercise_progression` and the active program day exercise).
    - Suggested variants (rule-based: same primary muscle, same movement pattern, different equipment, ordered by how many times the user has logged each).

## Web UI

Route: `/exercises/[id]/analytics`. Linked from history view and from insight cards.

Layout:
- Header: exercise name, primary/secondary muscles, equipment.
- 4-tile stat row: best e1RM, working weight, weekly sets, last session.
- Tabs: Trends, Sets, Variants.
  - Trends: line charts.
  - Sets: scatter and a sortable table.
  - Variants: a list with quick "Swap in program" actions.

## Deliverables

1. API endpoint with the response shape.
2. Web route + components (reuse `TrendChart`).
3. Tests against fixtures for e1RM math, slope detection, and variant ranking.

## Acceptance criteria

- Page loads under 600ms with a year of data.
- Predicted next session matches what the progression engine would produce.

## Dependencies

- `02.03 History and exercise detail (web)`
- `04.01`-`04.03`
- `05.01`

## Out of scope

- Forecasting beyond next session (later, possibly ML-driven).
