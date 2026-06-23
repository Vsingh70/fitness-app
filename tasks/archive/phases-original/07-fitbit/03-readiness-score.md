# 07.03 Readiness and recovery score

## Context

Daily readiness score using Fitbit data (sleep, RHR, HRV) to gauge how hard to train. Fed into the fatigue accumulator in 04.03 and surfaced on Today.

## Goal

A simple, transparent readiness score we compute ourselves (so it works even if the user's Fitbit plan lacks a native readiness score).

## Formula

Compute daily on `daily_metrics`:

```
sleep_component = clip(sleep_minutes / 480, 0, 1) * 40
rhr_component = clip(1 - (rhr - baseline_rhr) / 10, 0, 1) * 30   # baseline = 14d median
hrv_component = clip(hrv_ms / baseline_hrv_ms, 0, 1) * 30        # if HRV present, else redistribute weight to sleep+rhr
readiness_score = round(sleep_component + rhr_component + hrv_component)
```

Stored in `daily_metrics.readiness_score`.

Severity bands:
- 0..40 low (recommend deload-style session or rest)
- 41..70 moderate (default targets, cap top RPE at 8)
- 71..100 high (proceed as planned, can push)

## Hook into Today

On the Today screen:
- StatTile: readiness score with color band.
- If low, prompt: "Want to reduce today's volume by 30%?" - if accepted, apply a one-day deload to the upcoming session's targets.

## API

- `GET /v1/readiness/today`
- `GET /v1/readiness/history?from=...&to=...`

## Job

`compute_readiness(user_id, date)`:
- Run nightly at 04:00 user-local.
- Also triggered when new daily_metrics arrives from a Fitbit sync.

## Deliverables

1. Computation function + tests.
2. API endpoints.
3. Today screen integration on web.
4. Hook into the fatigue accumulator: low readiness adds +1 to fatigue.

## Acceptance criteria

- Score is recomputed within 5 minutes of new sleep/HR data arriving.
- The Today screen surfaces readiness with a clear band color.
- "Reduce today's volume" applies and is reversible.

## Dependencies

- `07.01 Fitbit OAuth and data import`
- `04.03 Mesocycles and deloads`

## Out of scope

- ML-based readiness (heuristic-first; we may train a per-user model later).
