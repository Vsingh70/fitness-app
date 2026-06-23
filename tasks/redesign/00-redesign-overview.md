# Redesign overview

The single entry point for the current redesign. Everything under `tasks/redesign/`
supersedes the original phase folders (now in `archive/phases-original/`) and the
first editorial pass (`archive/redesign-direction-a/`). When this set disagrees
with archived specs or with shipped code, this set wins.

## Why this redesign exists

The shipped app has two problems that the first editorial pass did not solve:

1. The Programs feature is built on a rigid weekly model (`days_per_week`,
   `weeks`). It cannot express a training cycle that is not seven days long, it
   hard-codes 6 weeks and 4 days on new programs, it blocks activation unless the
   day count matches `days_per_week`, and it has no way to deactivate an active
   program. The fix is a data-model change, not UI polish. See `01-program-model.md`.
2. The information architecture sprawls: nine nav destinations, two calendar
   routes, and a Body page that overlaps a Health page. Several pages are visually
   ported but their purpose is unclear. See `03-information-architecture.md`.

## Decisions locked for this redesign

These were confirmed with the maintainer and are not open for re-litigation inside
the implementation tasks.

| Area | Decision |
|---|---|
| Backend latitude | Full stack. Schema, Alembic migration, FastAPI endpoints, regenerated OpenAPI types, and web frontend are all in scope. |
| Program model | Flexible microcycle plus mesocycle. A microcycle is an ordered list of slots; a mesocycle is N microcycle repetitions plus an optional appended deload. Replaces `days_per_week` / `weeks`. |
| Microcycle timing | Pure rotation. You advance to the next slot when you train, independent of the calendar weekday. An 8-slot microcycle takes as long as it takes. |
| Rest days | Explicit slots. Each slot in a microcycle is either a training day or a rest day. Cycle length is the total slot count. |
| Mesocycle and deload | Mesocycle length is N microcycle repetitions, set when periodization is chosen. Deload is an optional microcycle appended at the end, tracked separately. |
| Templates | Using a template copies it to a fully editable program with no link back to the source. |
| New-program entry | Creating a program always offers the template-or-blank choice, even when programs already exist. Not first-run only. |
| Duplicate | A program can be duplicated into a new editable fork (new program, no template link). Separate from save-as-template. |
| Save as template | A program can be saved as a reusable template with a chosen visibility: private to the owner, or shared with all training partners. |
| In-session temp swap | Sets log to the substitute's history; the original exercise pauses, neither credited nor stalled. |
| In-session permanent edit | Applies now and forward; a removed exercise stops progressing but its history is kept; logged sets stand. |
| In-session skip | Advances the rotation (slot consumed), marks the session skipped, and is neutral for progression (no stall). |
| Information architecture | Aggressively consolidate. Merge Body and Health into one Health surface, collapse to a single Calendar, fold the Exercises library into Workouts. |
| Today page | Command center. Readiness, today's session with Start, quick meal log, and a short insights feed. |
| Workflow spine | Program-centric. The active program drives Today and the Calendar; finishing a workout feeds Insights; insights loop back as program adjustments. |
| Design language | Unchanged. The editorial system in `00-overview/design-system.md` and `apps/web/src/styles/tokens.css` stays canonical. Spacing and type-scale fixes are tuning, not a new system. |
| Food data | Drop FatSecret. Self-host free USDA FoodData Central + Open Food Facts bulk data in the `foods` table, searched via the existing pg_trgm index. Free is a hard requirement; no paid provider. |
| Structured work | First-class. Rest-pause/cluster sub-bouts, interval/HIIT rounds, and warm-up blocks of varied movements get real schema, not flags on repeated rows. Warm-up never counts as working volume. |
| Freestyle workouts | First-class. A session can start empty with no program; per-exercise progression still tracks. A program just pre-fills when active. |
| Rest timer | The default rest is adjustable mid-workout and optionally savable as the user default. |

## Spec set

Read in order.

1. `00-redesign-overview.md` (this file) — scope, decisions, status.
2. `01-program-model.md` — the flexible microcycle and mesocycle model, full stack.
3. `02-programs-screens.md` — the Programs UI built on the new model.
4. `03-information-architecture.md` — nav consolidation and page connectivity.
5. `04-page-specs.md` — per-page purpose for every surface in the new IA.
6. `06-workout-session.md` — the core logging loop: set rows, adjustable rest timer,
   offline, first-class structured work (rest-pause/cluster, intervals, warm-up blocks),
   and freestyle sessions. The base that `05` extends.
7. `05-active-session.md` — in-session exercise swap, permanent edit, and skip, and how
   each feeds progression. Builds on `06`.
8. `07-nutrition.md` — replaces FatSecret with a free, self-hosted USDA + Open Food
   Facts food-data stack.

Canonical references that survive the redesign:

- `00-overview/data-model.md` — schema reference. Update it as part of `01`.
- `00-overview/api-conventions.md` — response envelope and error codes. Unchanged.
- `00-overview/design-system.md` — editorial design language. Unchanged.

## Build order

The model change gates everything in Programs, and the IA change gates the
per-page work. Suggested sequence:

1. `01-program-model.md` backend: migration, models, endpoints, OpenAPI regen.
2. `02-programs-screens.md` web: onboarding, active spine, builder, templates.
3. `03-information-architecture.md`: nav consolidation and route merges.
4. `04-page-specs.md`: redesign each remaining surface against its stated purpose.
5. `06-workout-session.md`: the core logging loop and structured-work schema (depends
   on the rotation hooks from `01`).
6. `05-active-session.md`: the in-session edit and skip flows, on top of `06`.
7. `07-nutrition.md`: the food-data ingest pipeline (independent of the program work,
   can run in parallel).
8. iOS catches up per surface once the web shape is settled (was the open gap
   before this redesign and stays so).

## Status

Planning complete. No implementation has started. The next action is to implement
`01-program-model.md` on a branch.
