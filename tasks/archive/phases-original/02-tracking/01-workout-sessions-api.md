# 02.01 Workout sessions API

## Context

Core feature. A workout session is a logged training session containing exercises and sets. May be unlinked (free-style logging) or linked to a `scheduled_workout`.

Reference: `00-overview/data-model.md` (workout_sessions, workout_exercises, sets).

## Goal

Full CRUD over workout sessions and their nested exercises and sets, with support for every `tracking_type`.

## Schema

Create migrations for `workout_sessions`, `workout_exercises`, `sets`, exactly per data-model.md. Add these indexes:

- `workout_sessions(user_id, started_at desc)` partial where `deleted_at is null`.
- `workout_exercises(workout_session_id, position)`.
- `sets(workout_exercise_id, set_index)`.
- `sets(workout_exercise_id) include (weight_kg, reps, rpe)` for fast last-session lookups.

## Endpoints

### Sessions
- `POST /v1/workout-sessions` body `{ name?, scheduled_workout_id?, started_at? }`. Defaults `started_at` to now.
- `GET /v1/workout-sessions` cursor paginated, ordered by `started_at desc`. Filters: `from`, `to`, `program_id`.
- `GET /v1/workout-sessions/{id}` returns session + exercises + sets fully nested.
- `PATCH /v1/workout-sessions/{id}` update `name`, `notes`, `bodyweight_kg`, `perceived_exertion`, `started_at`, `ended_at`.
- `POST /v1/workout-sessions/{id}/finish` sets `ended_at = now` and triggers a background job to (a) recompute `exercise_progression`, (b) detect PRs and mark `sets.is_pr`, (c) enqueue an analytics rollup.
- `DELETE /v1/workout-sessions/{id}` soft delete.
- `POST /v1/workout-sessions/{id}/restore` clears `deleted_at` if within 30 days.

### Exercises within a session
- `POST /v1/workout-sessions/{id}/exercises` body `{ exercise_id, position?, notes? }`.
- `PATCH /v1/workout-exercises/{id}` `notes`, `position`.
- `DELETE /v1/workout-exercises/{id}` cascades to sets.
- `POST /v1/workout-exercises/{id}/reorder` body `{ position }`. Server reorders siblings.

### Sets
- `POST /v1/workout-exercises/{id}/sets` body matches `tracking_type` of the parent exercise. Server validates the right fields are present:
  - `weight_reps`: `weight_kg`, `reps` required.
  - `bodyweight_reps`: `reps` required, `weight_kg` optional (added load).
  - `weighted_bodyweight`: `weight_kg`, `reps` required (added load).
  - `time_only`: `duration_seconds` required.
  - `distance_time`: `distance_meters`, `duration_seconds` required.
  - `weight_time`: `weight_kg`, `duration_seconds` required.
  - `weight_reps_distance`: all three required (farmer carries etc.).
  - `distance_time_pace`: distance + duration, server computes pace.
  - `cardio_machine`: `duration_seconds` required, optional `distance_meters`, `calories`, `average_hr`.
- `PATCH /v1/sets/{id}` partial update.
- `DELETE /v1/sets/{id}` hard delete (and re-index siblings).

## PR detection

When a session is finished, for each `workout_exercise`:
- For weight_reps: compute e1RM (Epley: `w * (1 + reps/30)`). Mark the heaviest e1RM set as `is_pr` if it exceeds the user's prior max e1RM for that exercise.
- For bodyweight_reps: PR if max reps exceeds prior max.
- For distance_time: PR if best pace exceeds prior best at that distance bucket.
- Store the user's previous max in `exercise_progression` (created by progression task; for this task just write the field if the row exists, else create a minimal row).

## Idempotency

`POST` endpoints for sessions and sets accept `Idempotency-Key`. Required for the iOS app's offline queue replay.

## Deliverables

1. Migrations for all three tables + indexes.
2. SQLAlchemy models with proper relationships.
3. Pydantic schemas with tracking_type-aware validation (use discriminated unions or a `model_validator` per type).
4. Routers and service layer.
5. Background job `finalize_session` triggered by the finish endpoint.
6. Tests:
   - Create session, add exercises, add sets across all tracking_types.
   - Finish session marks PRs correctly.
   - Validation rejects wrong fields for the tracking_type.
   - Soft delete hides from list but is retrievable; restore works.

## Acceptance criteria

- A full session lifecycle is logged via API in under 50ms per write call locally.
- The nested `GET /v1/workout-sessions/{id}` returns in a single query (no N+1).
- PR detection passes the test fixture with hand-checked expected results.

## Dependencies

- `01.02 FastAPI skeleton`
- `01.03 Auth`
- `01.04 Exercise library`

## Out of scope

- Templates, programs (next phase).
- Progression engine (next phase). PR detection writes a minimal `exercise_progression` row but doesn't compute recommendations.
