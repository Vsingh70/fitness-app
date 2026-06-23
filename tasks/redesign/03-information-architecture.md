# Information architecture

How the app is organized and how the surfaces connect. This consolidates the nav and
sets the program-centric spine. Per-page purpose lives in `04-page-specs.md`.

## 1. Current state

Nine nav destinations in `apps/web/src/components/layout/nav-items.ts` (Today,
Workouts, Programs, Exercises, Nutrition, Insights, Body, Health, Settings) plus two
calendar routes (`/calendar` and `/workouts/calendar`) and a Help route. Body and
Health both surface wearable and body metrics. Exercises is a desktop-only library
that duplicates discovery already reachable from Workouts. The result is sprawl that
makes "what is this page for" hard to answer.

## 2. Target nav

Six primary destinations. Fewer, each with one clear job.

| Destination | Absorbs | Job |
|---|---|---|
| Today | (new home) | Command center: readiness, today's session, quick meal log, insights feed. |
| Workouts | Exercises library, both calendars | Log and browse training. History, the single calendar, and the exercise library live here. |
| Programs | | Build and run the active program (the spine). |
| Nutrition | | Log-first food tracking. |
| Health | Body | One surface for wearable sync and body metrics. |
| Insights | | Trends, volume, and recommendations. |

Settings stays reachable but off the primary bar (gear in the top bar). Help stays as
a top-bar link.

### Route moves

- Merge `/calendar` and `/workouts/calendar` into one calendar under Workouts. Delete
  the duplicate route; redirect the old path.
- Fold `/exercises` and `/exercises/[id]` under Workouts as a library tab and the
  exercise detail page (the per-exercise page in the design brief is unchanged in
  content, only its parent surface moves).
- Merge `/body` into `/health`. The new Health page has a Metrics section (weight and
  body measurements, formerly Body) and a Wearable section (steps, sleep, readiness,
  formerly Health). Resolve the Fitbit-to-Google-Health migration here.
- Update `nav-items.ts`, `desktop-sidebar.tsx`, and `mobile-tabbar.tsx`. Keep the
  five-item mobile tab bar: Today, Workouts, Programs, Nutrition, Insights. Health and
  Settings are desktop sidebar plus deep links from Today (readiness tile to Health).

## 3. Program-centric spine

The active program is the backbone. The connections to enforce:

- **Programs to Today**: Today's session is the current rotation slot of the active
  program (`GET /v1/programs/{id}/position`). No active program means Today shows a
  rest or onboarding state, not an empty hero.
- **Programs to Calendar**: the calendar projects the rotation forward from the
  current position. Because timing is pure rotation (`01-program-model.md`), the
  calendar shows planned slots in order, not weekday-pinned cells.
- **Workout to Insights**: finishing a session feeds volume rollups and
  recommendations. The summary screen surfaces next-session recommendations.
  In-session divergences (temp swap, permanent edit, skip) feed progression per
  `05-active-session.md`: substitutes pause the original, skips advance the rotation
  neutrally, permanent edits rewrite the program forward.
- **Insights to Programs**: an insight card (plateau, imbalance) deep-links to the
  exercise or program and offers an adjustment that writes back to the program.

This loop is the product. Every page either feeds it or reads from it.

## 4. Acceptance

- [ ] Nav shows six destinations; mobile tab bar shows five.
- [ ] One calendar route; the duplicate is removed and redirected.
- [ ] Exercises library and exercise detail live under Workouts.
- [ ] Body is merged into Health with Metrics and Wearable sections.
- [ ] Today's session is driven by the active program's rotation position.
- [ ] Insight cards deep-link and can write program adjustments.
