# 07.02 Push workouts to Fitbit

## Context

When a user finishes a workout in our app, post it to Fitbit so their unified activity log + calorie tracking on the Fitbit side stays accurate.

## Goal

A worker that posts finished sessions to Fitbit and tracks what's been pushed.

## Schema

Add to `workout_sessions`:
- `fitbit_log_id` text nullable (Fitbit's activity log id once pushed).
- `fitbit_pushed_at` timestamptz nullable.

## Mapping

- `started_at`, `ended_at` -> Fitbit activity start time and duration.
- Activity type: a server-side mapping from our exercise set to Fitbit activity types. For a typical mixed strength session, use `Strength Training` (activityId 3001). If the session is predominantly cardio (detect by ratio of cardio exercises), use the matching Fitbit cardio type.
- Calories: if user has Fitbit, use Fitbit's HR-derived estimate by leaving calorie field blank and letting Fitbit compute. Otherwise our own estimate from MET tables.
- Notes: include workout name and total volume in the description.

## Job

`push_session_to_fitbit(session_id)`:
- Skip if already pushed.
- POST to `/1/user/-/activities.json`.
- Store returned `activityLog.logId` in `fitbit_log_id`.
- On 409 / duplicate, mark pushed without retry.

Triggered automatically from `finalize_session` if the user has a connected Fitbit; user can opt out in settings (`auto_push_to_fitbit` boolean on `users` default true).

## Endpoints

- `POST /v1/workout-sessions/{id}/push-to-fitbit` manual trigger.
- `DELETE /v1/workout-sessions/{id}/fitbit-link` removes the linkage (does not delete from Fitbit; leave that to the user).

## Deliverables

1. Schema + migration.
2. Mapping logic.
3. Worker.
4. Hook in finalize.
5. Setting toggle in `/v1/me` PATCH and on the web settings page.
6. Tests with mocked Fitbit client.

## Acceptance criteria

- A finished session is pushed within 1 minute on a connected account.
- Repushes do not create duplicates on Fitbit.
- Disconnecting Fitbit cleanly stops pushes (worker checks connection exists).

## Dependencies

- `07.01 Fitbit OAuth and data import`
- `02.01 Workout sessions API`

## Out of scope

- Editing pushed activities (Fitbit's API is limited; we accept this).
