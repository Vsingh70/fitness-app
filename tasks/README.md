# Tasks

The spec for gym-app. The active work is the redesign under `redesign/`. The original
phase-by-phase build plan is finished and archived; treat the redesign set as
canonical when it disagrees with archived specs or with shipped code.

## Layout

- `redesign/` — the active redesign. Start at `redesign/00-redesign-overview.md`.
- `00-overview/` — canonical references that survive the redesign: `data-model.md`,
  `api-conventions.md`, `design-system.md`.
- `archive/` — finished or superseded material, kept for history:
  - `phases-original/` — the original numbered build plan (foundation through
    onboarding). The backend shipped from this; it is not the current source of truth.
  - `redesign-direction-a/` — the first editorial pass (programs and nutrition
    Direction A, editorial handoff, iOS). Superseded by `redesign/`.
  - `design-canvas-export/` — the design-tool export and screenshots used during the
    first editorial pass.
  - `programs-workflow-original-feedback.md` — the maintainer's bug list that prompted
    this redesign. Folded into `redesign/02-programs-screens.md`.

## The redesign in one paragraph

Programs is rebuilt on a flexible microcycle and mesocycle model that replaces the
rigid `days_per_week` and `weeks` columns: a microcycle is an ordered list of slots
(training or rest) of any length, advanced by pure rotation; a mesocycle is that
microcycle repeated N times plus an optional appended deload. The nav is consolidated
from nine destinations to six (Body merges into Health, the two calendars become one,
the exercise library folds into Workouts), Today becomes a command center, and the
active program is the spine that drives Today and the calendar while finished workouts
feed Insights that loop back as program adjustments. Workouts can be run from the program
or freestyle with no program, structured work (rest-pause, intervals, warm-up blocks of
varied movements) is modeled first-class, and the rest timer is adjustable mid-session.
Mid-workout the user can swap an exercise for one session, permanently edit it in the
program, or skip the session, each feeding progression differently. Nutrition keeps its
log-first shape but drops FatSecret for a free, self-hosted USDA plus Open Food Facts
food database. Backend changes (schema,
migration, API, regenerated types) are in scope.

## How to use these files

Each redesign file is self-contained: scope, decisions, deliverables, acceptance.
Implement in the order listed in `redesign/00-redesign-overview.md`. Point Claude Code
at one file at a time.

## Style rules

- No em dashes or en dashes in prose anywhere (code comments, READMEs, UI copy).
- Concise plain language. Direct answers before explanations.
- Sentence case headings.
- Python: ruff plus black, type hints everywhere, Pydantic v2 models.
- TypeScript: strict mode, no `any`, Zod for runtime validation.
- Swift: SwiftUI-first, async/await, no Combine unless required.
