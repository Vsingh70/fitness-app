# 05.02 Strong and weak point analysis

## Context

The user wants to know which muscles are strong, which are weak, which are stagnating, and which are imbalanced. Heuristics first, with LLM-generated rationale strings layered on (same pattern as 04.04).

Reference: `00-overview/data-model.md` (analytics_insights).

## Goal

A pure-heuristic engine that produces `analytics_insights` rows, plus the LLM rationale job.

## Heuristics

### Weak / strong muscle (relative strength)
- For each major muscle, find its representative compound (table mapping: chest -> bench, quads -> back squat, hamstrings -> Romanian deadlift, lats -> pull-up, etc.).
- Compute the user's best e1RM in the last 12 weeks for each.
- Normalize by bodyweight and gender-typical multipliers (use Wilks-style table simplified to per-lift bodyweight ratios; ship the table in `apps/api/app/services/analytics/strength_norms.py`).
- Result: strength percentile per muscle relative to defaults.
- Bottom 25% across muscles -> insight kind `weak_muscle`.
- Top 25% -> `strong_muscle`.

### Stagnation
- For each exercise the user has logged at least 6 times in the last 12 weeks: fit a simple linear regression on e1RM over time.
- If slope is <= 0 and noise (residual stddev) is below threshold, flag as `stagnation` for that exercise.

### Imbalance
- Push:pull weekly working sets in the last 4 weeks. If ratio falls outside [0.7, 1.4], emit `imbalance` insight.
- Quad:hamstring ratio. Outside [0.6, 1.5] flags `imbalance`.
- Anterior delt vs rear delt sets. Outside [0.5, 1.5] flags.

### Undertrained muscle
- Average weekly working sets in last 4 weeks below 8 for a primary mover.
- Emit `undertrained` with the suggested target range.

## Service

`apps/api/app/services/analytics/insights.py`:

```python
async def compute_insights_for_user(user_id: UUID) -> list[NewInsight]: ...
```

Pure read + insert. Insights have a `surfaced_at`; new runs upsert by `(user_id, kind, subject)` so we don't spam.

## Job

`recompute_insights` runs nightly per user after the rollup job. Also exposed as a manual `POST /v1/insights/recompute`.

## Endpoints

- `GET /v1/insights`
  - Query: `kind`, `severity`, `dismissed` (default false).
  - Cursor paginated.
- `POST /v1/insights/{id}/dismiss`.

## LLM rationale

Same pattern as 04.04. Background job fills in `rationale` per insight with a one-sentence explanation.

## Web UI

Insights live on `/insights`:
- Top section: prioritized insight cards (severity `action` first).
- Each card: subject (muscle or exercise), short rationale, "Show data" reveals the supporting chart, dismiss button, "Adjust program" link that deep-links to the program editor with the relevant exercise pre-focused.

## Deliverables

1. Strength norms table.
2. Heuristic functions, each pure and unit-tested.
3. Nightly job + manual recompute endpoint.
4. LLM rationale job hooked into Ollama.
5. Web UI components.
6. Tests with seeded mock data verifying each heuristic correctly fires/doesn't fire at boundary conditions.

## Acceptance criteria

- Mock user with bench at 1.5x BW, squat at 1.0x BW correctly flags chest as strong and quads as moderate.
- Mock user with stagnant deadlift e1RM over 8 weeks gets a `stagnation` insight for deadlift.
- Insight dedup works: re-running doesn't create duplicates.

## Dependencies

- `05.01 Per-muscle volume and weekly rollups`
- `04.04 LLM rationale generation`

## Out of scope

- Cross-user comparison (no social layer).
- ML-based detection (heuristics-first is what we chose).
