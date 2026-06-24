# 03.03 Scheduling and calendar

## Context

When a program is active, the system generates `scheduled_workouts` rows. Users see them on a calendar, can drag to reschedule, and can mark days as skipped, deload, or completed (the latter happens automatically when a session linked to the scheduled workout finishes).

## Goal

Reliable scheduling, drag-to-reschedule, and a calendar view.

## API

- `GET /v1/scheduled-workouts` filters: `from`, `to`. Returns scheduled rows with linked program day metadata.
- `PATCH /v1/scheduled-workouts/{id}` update `scheduled_for` (reschedule), `status` (skip / unskip), `is_deload`, `mesocycle_week`.
- `POST /v1/scheduled-workouts/{id}/start` creates a `workout_session` linked to this scheduled workout. Returns the new session.

## Logic

- A program's activation creates scheduled workouts week by week. For weekly programs, the day-of-week comes from `weekday_offset + program_day.day_index`.
- When a session linked to a scheduled workout is finished, the scheduled workout status becomes `completed`.
- Reschedule cascades: if the user shifts week 3 day 1 to a later date, later days are not auto-shifted. Provide a "Shift remaining program by X days" option that the user opts into.

## Web UI

Route: `/calendar`. Month view by default, week view available.
- Each day shows scheduled workouts as chips colored by status (planned/in_progress/completed/skipped). Deload weeks tinted differently.
- Drag-and-drop reschedule (uses `dnd-kit`). Hold Shift to "Shift remaining program from here".
- Click a chip to open the scheduled workout detail with a Start button.

## Notifications (server-side prep)

Add a `notifications` table now (we'll wire up delivery later):
- `id`, `user_id`, `kind` enum, `payload` jsonb, `scheduled_for`, `sent_at` nullable, `read_at` nullable.

Background job `enqueue_workout_reminders` runs daily at 06:00 local-to-user (using user timezone) and inserts reminders for that day's planned workouts. Delivery (push, email) is a later task.

## Deliverables

1. API endpoints and logic.
2. Web calendar UI with dnd.
3. Notifications table + scheduler job (no delivery yet).
4. Tests: activation -> verify scheduled workouts. Reschedule with and without cascade.

## Acceptance criteria

- Activating an 8-week PPL program creates 48 scheduled workouts.
- Dragging a workout to a new date updates `scheduled_for` and re-renders.
- Skipping a workout updates status; unskipping restores planned.

## Dependencies

- `03.01 Program templates`
- `03.02 Program builder (web)`
- `02.01 Workout sessions API` (for the "Start" link)

## Out of scope

- Push notification delivery (later).
