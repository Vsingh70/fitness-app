# Active session: in-session edits and skip

How a workout in progress can diverge from the program, and how those divergences
feed progression and tracking. This pulls the active-session logger into the redesign
scope (it was previously deferred). It lives under Workouts in the IA
(`03-information-architecture.md`) but is specified here because every action touches
the active program and the progression engine.

Depends on the model in `01-program-model.md` (rotation position, slots) and the
program-centric spine. The progression-engine math itself stays out of scope; this
spec defines the signals the engine consumes, not the formulas.

## 1. Context

A session is the current rotation slot of the active program, started from Today or
Workouts. Mid-session the user may need to deviate: substitute a movement they cannot
do right now, change the program itself, or abandon the session. Each path records a
different signal so progression and history stay honest.

## 2. Temporary swap (one session only)

Use case: on vacation, no barbell, swap barbell bench for dumbbell bench just for
today.

Behavior:

- On a session exercise, a "Swap for this session" action opens the exercise picker.
  Picking a substitute replaces the movement for this session only. The program is not
  changed.
- The set rows now log against the substitute exercise.

Progression and tracking (decision: substitute tracked, original paused):

- The logged sets count toward the **substitute's** own exercise history and
  progression state, exactly as if the user had chosen it.
- The **original** exercise is neither credited nor penalized. Its progression state
  does not advance and the session is not counted as a miss or stall for it. It simply
  pauses for this slot.
- The session record marks the exercise as substituted, retaining the link to the
  original so the history reads "dumbbell bench (in place of barbell bench)".

Data: on the session exercise row, record `substituted_for_exercise_id` (the original)
when a temporary swap occurs. The progression engine skips exercises that are
substituted-for when computing stall and progress for the original.

Out of scope for v1: remembering a preferred substitute across sessions. Each swap is
a fresh choice.

## 3. Permanent change or removal (writes to the program)

Use case: the user decides an exercise is wrong and wants to fix the program, not just
today.

Behavior:

- A "Change in program" / "Remove from program" action on a session exercise edits the
  **active program's** slot, the same write the builder makes.
- A change can swap the exercise or edit its targets (sets, reps, intensity). A removal
  drops it from the slot.

Progression and tracking (decision: apply now, forward; history kept):

- The edit applies immediately and to all future cycles. There is no wait for the next
  mesocycle.
- A **removed** exercise's progression state stops advancing but its history is
  **retained** (never deleted), so past trends still render on the exercise page.
- A **newly added** exercise starts with fresh progression state.
- The sets the user already logged this session **stand**; the edit does not rewrite
  the in-progress session's existing data.

Data: these reuse the program slot endpoints from `01-program-model.md` (update slot
exercise, delete slot exercise). No new fields beyond what the builder already needs.

## 4. Skip the workout (mid-session)

Use case: the user starts, then cannot continue and abandons the session.

Behavior:

- A "Skip workout" action ends the session as skipped. Any sets already logged are
  kept on the session record (a partial session is still history).

Rotation and progression (decision: advance, mark skipped, neutral):

- The rotation pointer **advances** to the next slot. The skipped slot is consumed, not
  repeated. (Implements `01`'s "completing or skipping advances the position".)
- The session is marked `skipped`.
- Progression treats the skip as **neutral**: no exercise progresses, and the skip does
  **not** feed the stall signal, so a one-off skip never triggers deload-on-stall.

Data: `scheduled_workouts.status = skipped` (status enum already exists). The rotation
advance logic in `program_progress` runs on skip exactly as on completion. The
progression engine ignores skipped sessions when counting consecutive successes or
failures.

## 5. Interaction summary

| Action | Program changed? | Rotation pointer | Original exercise progression | History |
|---|---|---|---|---|
| Temp swap | No | n/a (same session) | Paused, no stall | Substitute logged, linked to original |
| Permanent change | Yes, now and forward | n/a | Removed: stops, kept. Added: fresh | Retained |
| Skip workout | No | Advances, slot consumed | Neutral, no stall | Partial session kept, marked skipped |

## 6. Constraints (carry the design brief rules)

- Errors never block the session: a failed sync on a swap or skip still saves locally
  and shows a quiet badge, no mid-session modal (design brief section 7).
- No modal stacking deeper than two: the swap picker is one sheet; do not nest.
- One-handed: swap, change, and skip actions are reachable in the bottom 60 percent of
  the screen during a session.

## 7. Acceptance

- [ ] A session exercise can be temp-swapped; sets log to the substitute, the original
      neither progresses nor stalls, and history shows the substitution link.
- [ ] A session exercise can be changed or removed in the program; it applies now and
      forward, removed-exercise history is retained, logged sets stand.
- [ ] A workout can be skipped mid-session; the pointer advances, the session is marked
      skipped, and progression treats it as neutral (no stall).
- [ ] The progression engine ignores substituted-for originals and skipped sessions
      when computing stall and progress.

## 8. Out of scope

- Progression-engine formulas (separate feature; this defines inputs only).
- Persisted preferred substitutes across sessions.
- iOS implementation (catches up after the web shape settles).
