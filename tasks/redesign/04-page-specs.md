# Page specs

Purpose and redesign intent for each surface in the target IA (`03-information-architecture.md`).
Programs is fully specified in `02-programs-screens.md` and only summarized here.
Each page states what it is for, what changes, and how it connects to the spine.

## Today (command center)

Purpose: the daily landing surface and the answer to "what do I do now".

- Layout: readiness tile (from Health), today's session card (the active program's
  current rotation slot, with Start), a quick meal-log entry, and a short insights
  feed (top 1 to 3 recommendation cards).
- Connects: reads the program position, links to Workouts to start, to Nutrition to
  log, to Insights and Health for detail.
- States: no active program shows "pick a program" routing to Programs onboarding; a
  rest slot shows a quiet rest state with the next training slot named; no wearable
  shows readiness as "Connect" linking to Health.

## Workouts (training home)

Purpose: log training, browse history, find exercises. Absorbs the Exercises library
and the single calendar.

- Sections or tabs: Active or scheduled session at top, recent history, the calendar
  (one route now), and the exercise library (was `/exercises`).
- Exercise detail (the per-exercise page: Trends, Sets, Variants, Notes) is unchanged
  in content; its parent is now Workouts.
- Connects: starting a session uses the program slot; finishing routes to the summary
  and feeds Insights.
- Active session: mid-workout the user can temp-swap an exercise, permanently change or
  remove it in the program, or skip the workout. Each affects progression and the
  rotation differently. Fully specified in `05-active-session.md`.
- Calendar: projects the rotation forward in order (pure rotation, not weekday cells).

## Programs (the spine)

Purpose: build and run the active program. Fully specified in `02-programs-screens.md`
and modeled in `01-program-model.md`. Summary: onboarding for first run, an
active-program spine with the microcycle cycle bar, a builder with flexible slots and
mesocycle length, and a multi-program library with activate, deactivate, and delete.

## Nutrition (log-first)

Purpose: fast food logging. Keep the Direction-A log-first shape (calorie masthead,
large quick-add search, P/C/F strip, flexible or plan mode). This page was not flagged
as broken; the redesign work here is purpose clarity and consistency with the new
spacing and type tuning, not a rebuild.

- Confirm the flexible-vs-plan mode reads cleanly and the quick-add is the primary
  action. Apply the same spacing and type pass as Programs.
- Mode switching: the flexible-vs-plan choice is not locked at onboarding. The user can
  switch either direction anytime, from Settings and from a small control on the
  nutrition day header. `nutritionMode` is an account preference, switchable freely.
  - Flexible to plan: prompt to pick which plan to activate; if none exists, route to
    the plan create wizard, then return in plan mode.
  - Plan to flexible: the day reverts to free-form meals.
  - Non-destructive in both directions: meals already logged today are never deleted.
    On a switch they are re-presented under the new mode (plan slots become free-form
    "Meal 1..n" and vice versa); macros and totals are unchanged.
- Food data: the substantive change here is the data source behind quick-add and
  barcode. FatSecret is dropped for a free, self-hosted USDA + Open Food Facts stack.
  Fully specified in `07-nutrition.md`. The page layout is unchanged.
- Connects: the quick meal-log on Today deep-links here; daily totals feed nothing in
  the program spine directly but belong to the same daily snapshot.

## Health (wearable plus body, merged)

Purpose: one surface for everything the body and wearables report. Merges Body and
Health.

- Sections: Metrics (weight and body measurements, formerly Body, manual entry) and
  Wearable (steps, sleep, resting HR, readiness, formerly Health, synced).
- Resolve the Fitbit-to-Google-Health migration here: one connection card, one status,
  whichever provider is active.
- Connects: readiness here is the source for the Today readiness tile.

## Insights (analytics)

Purpose: trends, per-muscle volume, and recommendations. Labeled Insights in nav,
route stays `/analytics`.

- Keep the volume heat panel, per-exercise trends, and weekly insight cards.
- Make insight cards actionable: each deep-links to the relevant exercise or program
  and, where applicable, offers an adjustment that writes back to the active program.
  This closes the program-centric loop.
- Apply the spacing and type pass.

## Settings

Purpose: appearance (accent, theme), units, connections (defers to Health for the
wearable connection), and the active-program selector. Off the primary nav, reachable
from the top bar. Light redesign only: align to the tuned spacing and type.

## Cross-page acceptance

- [ ] Today is driven by the program rotation and links out to each surface.
- [ ] Workouts contains history, the single calendar, and the exercise library.
- [ ] Health shows merged Metrics and Wearable sections with one connection.
- [ ] Insight cards deep-link and can adjust the active program.
- [ ] Every redesigned surface uses the tuned spacing and type scale, light and dark.
