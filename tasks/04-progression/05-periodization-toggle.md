# 04.05 Periodization toggle (continuous vs block)

## Context

Today a program is built around mesocycles and deloads (see `04.03 Mesocycles and deloads`): a block that ramps, peaks, deloads, and ends. Some users do not want a split that ends. They want to pick exercises and just keep progressing indefinitely, with no forced block boundary or reset.

We need a per-program choice between two lifecycle modes:

1. Periodized (block): the current behavior. Finite mesocycle, planned deloads, an end point, then the user starts a new block.
2. Continuous (open-ended): the program never ends on its own. Progression keeps applying every session. Deloads are optional and only triggered reactively (stall detected or user asks), not scheduled.

Reference: `03-programming/01-program-templates.md`, `04-progression/03-mesocycles-deloads.md`, `00-overview/data-model.md` (programs).

## Goal

Let a user create or convert a program as continuous, where the progression engine keeps driving set, rep, and load increases with no scheduled mesocycle end, and the UI never nags about a block ending.

## Data model

- `programs.periodization_mode` enum: `block`, `continuous`. Default `block` to preserve current behavior.
- For `continuous`:
  - No `mesocycle_length_weeks` requirement and no scheduled deload week.
  - Optional `auto_deload_on_stall` bool (default true): when the progression or stagnation heuristics flag a stall on a lift, suggest a reactive deload for that lift only, not the whole program.
- A migration that adds the column and backfills existing rows to `block`.

## Progression behavior

- Block mode: unchanged.
- Continuous mode:
  - The progression engines (linear, double, RPE) keep running every session with no week-index ceiling.
  - No "block complete" event is ever emitted.
  - Deloads are reactive only. When a lift stalls (reuse the existing stall detection from analytics), the recommendation surface offers a per-lift deload the user can accept or dismiss.

## API

- Program create and update accept `periodization_mode` and `auto_deload_on_stall`.
- `GET /v1/programs/{id}` returns both fields.
- The active-program and next-session endpoints must not return block-end or deload-week framing when the program is continuous.

## Web UI

- Program builder: a clear two-option control at the top of program setup, "Periodized block" vs "Just keep progressing", with one line of helper copy each.
- When continuous: hide mesocycle length and scheduled deload inputs. Show the reactive deload toggle instead.
- Today and program views: for continuous programs, replace any "week X of Y" or "block ends in" labels with a simple streak or session count.

## Deliverables

1. Migration for the two new program columns.
2. Engine changes so continuous mode never hits a block boundary and deloads only fire reactively.
3. API surface (create, update, reads) carrying the new fields and the corrected framing.
4. Web program builder control plus the Today and program label changes.
5. Tests: a continuous program runs many sessions past a normal block length with progression still applying and no block-end event; a stalled lift in continuous mode produces a per-lift deload suggestion only.

## Acceptance criteria

- A user can create a program that never ends and keeps getting progression recommendations indefinitely.
- Switching an existing block program to continuous stops all scheduled deload and block-end prompts immediately.
- A stall on one lift in continuous mode offers a deload for that lift without resetting the whole program.

## Dependencies

- `04.01 Linear and double progression`
- `04.02 RPE-based progression`
- `04.03 Mesocycles and deloads`
- `05.02 Strong and weak points` (stall detection reused for reactive deloads)

## Out of scope

- iOS parity (follow-up under `08-ios/`).
- New progression algorithms. This task only changes the lifecycle, not the math.
