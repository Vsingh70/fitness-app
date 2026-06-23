# 08.02 iOS workout tracking

## Context

iOS equivalent of `02.02 logging UI` and `02.03 history`. Same data, native UX.

## Goal

A workout-in-progress experience optimized for one-handed phone use at the gym.

## Screens

### Today (`Features/Today/TodayView.swift`)
- Big "Start workout" button (scheduled workout if any, else empty).
- Recent sessions card.
- Recent PRs card.
- (Readiness tile placeholder for 07.03.)

### Workout in progress (`Features/Workouts/WorkoutSessionView.swift`)
- Top bar: session name (tap to edit), elapsed timer, Finish button.
- Exercise list with sets table per exercise.
- Tap a cell to bring up a custom numeric keypad sheet optimized for kg/lbs and reps. Faster than the system keyboard.
- Swipe-to-delete on sets.
- Drag-to-reorder on exercises (long press + drag).
- Bottom: "Add exercise" opens `ExercisePickerSheet`.
- Rest timer:
  - Auto-starts on set commit.
  - Persistent at the bottom of the screen while running.
  - Haptic at zero. Optional Live Activity to show on the lock screen.

### Workout summary
- Stat cards: duration, volume, sets, PRs.
- Per-muscle volume bar chart.
- Confetti only when a PR was set, gated on Reduce Motion.

### History (`Features/Workouts/HistoryView.swift`)
- List grouped by week.
- Calendar tab using `Calendar` view from iOS 17.

### Exercise detail (`Features/Workouts/ExerciseDetailView.swift`)
- e1RM and volume charts using Swift Charts.
- All sets list.

## Native niceties

- Live Activity for rest timer (Dynamic Island countdown).
- Quick action on home screen long-press: "Start empty workout".
- Shortcut: "Log set for {exercise}" via App Intents (later task; stub the AppIntent now).
- Haptics on set commit and PR.

## Offline

- Cache the active session in a local SwiftData store.
- All write mutations queue via a `MutationQueue` with `Idempotency-Key`.
- On connectivity restore, drain the queue.

## Deliverables

1. All views with previews.
2. ViewModels using `@Observable`.
3. Custom numeric keypad component.
4. Live Activity for rest timer.
5. SwiftData cache + mutation queue.
6. UI tests for the core flow: start session, add exercise, log 3 sets, finish.

## Acceptance criteria

- Logging a set is achievable in under 3 taps from anywhere in the workout screen.
- Rest timer Live Activity updates correctly and ends cleanly.
- Killing the app mid-workout and reopening restores the session intact.

## Dependencies

- `08.01 iOS app skeleton`
- `02.01 Workout sessions API`

## Out of scope

- Apple Watch app (separate task later).
