# 02.02 Workout logging UI (web)

## Context

The core daily-use screen. A user opens it, starts a session, and logs sets quickly.

Reference: `00-overview/design-system.md`, `02-tracking/01-workout-sessions-api.md`.

## Goal

A workout-in-progress screen that is fast, dense, and matches the iOS design language.

## Screens

### Today
Route: `/`. Shows:
- Scheduled workout for today if any, with a big primary CTA "Start workout".
- "Start empty workout" secondary action.
- Recent sessions list (last 5).
- Quick PR cards from the last 7 days.

### Workout in progress
Route: `/workouts/[id]`. Persistent across navigation: a sticky top bar shows the active session timer and the user can return to it from anywhere.

Layout:
- Header: session name (editable), elapsed time, finish button.
- Exercise list: each exercise is a card.
  - Header: exercise name, drag handle, menu (replace, reorder, remove).
  - Sets table: columns adapt to `tracking_type`:
    - weight_reps: Set | Previous | kg | Reps | RPE
    - bodyweight_reps: Set | Previous | Reps | RPE
    - distance_time: Set | Previous | Distance | Time
    - etc.
  - "Previous" column shows the last session's set at the same index for quick reference.
  - Tap a cell to edit inline. Tab/Enter moves to the next cell.
  - "Add set" row at the bottom of each exercise.
  - Rest timer auto-starts when a set is committed (uses `rest_seconds` from the program day if available, else 90s default; user can configure default in settings).
- "Add exercise" button at the bottom opens an `ExercisePicker` sheet.

### Workout summary
Route: `/workouts/[id]/summary`. Shown after finish:
- Total duration, total volume (sum of weight*reps), set count.
- PRs hit, with confetti-on-PR (subtle, honor `prefers-reduced-motion`).
- Per-muscle volume distribution chart.
- "Edit notes" and "Done" actions.

## Components needed

- `SessionTimer`: ticks every second using `requestAnimationFrame`, pauses on tab blur.
- `SetRow`: editable in place, validates per tracking_type.
- `RestTimer`: circular countdown, sound + tab title flash at zero.
- `ExercisePicker`: search-backed sheet with tabs Recent / Mine / All. Cached client-side with Tanstack Query.
- `SessionStickyBar`: top of layout when a session is active.

## State

- Active session is fetched on mount and held in Tanstack Query.
- Optimistic mutations for set add/edit/delete with rollback on error.
- All mutations use an `Idempotency-Key` generated client-side (UUID v4 per attempt).
- Offline: writes queue in IndexedDB and flush when online (use `localForage` + a small queue). Not strict offline-first; "best-effort" while a session is in progress.

## Keyboard

- Cmd/Ctrl + Enter: commit current set.
- Tab: next cell.
- Shift + Tab: previous cell.
- N: focus add-set in current exercise.
- E: focus add-exercise.

## Deliverables

1. All three routes implemented.
2. Components above.
3. Tanstack Query hooks: `useSession`, `useAddSet`, `useUpdateSet`, `useDeleteSet`, `useFinishSession`, etc.
4. Offline write queue.
5. Component tests with Vitest + React Testing Library for SetRow validation per tracking_type and RestTimer behavior.
6. A playwright e2e test that starts a session, logs 3 sets across 2 exercises, finishes, and verifies the summary.

## Acceptance criteria

- A power user can log a 6-exercise session entirely from the keyboard in under 60 seconds of UI interaction time.
- Network blips during a session do not lose data.
- The screen renders 60fps on a midrange laptop with 20+ exercises rendered.

## Dependencies

- `01.05 Next.js web skeleton`
- `02.01 Workout sessions API`

## Out of scope

- Voice logging.
- Apple Watch / wearable input (iOS app does this).
