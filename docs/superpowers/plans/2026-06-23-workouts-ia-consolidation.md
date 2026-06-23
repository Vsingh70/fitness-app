# Workouts Hub + IA Consolidation (web)

> Implements `tasks/redesign/03-information-architecture.md` (nav 9→6, merges) and the Workouts
> portion of `04-page-specs.md`. Built by the loop: Builder = `web-dev`, Checker = `qa-verifier`
> (`pnpm typecheck`/`lint`/`test`/`build`). Stacked on the web foundation
> (`feat/programs-flexible-model`, PR #8) — retarget to `main` after #8 merges.

**Goal:** Consolidate the nav to 6 destinations, merge Body into Health, fold the Exercises library
into a Workouts hub, and reuse the responsive + motion foundation — without breaking the app.

**Scope decisions (locked):**
- **In:** nav 9→6, Body→Health merge, Exercises folded into a Workouts hub, redirects, Settings off
  the primary bar, responsive + motion polish.
- **Deferred (next phase, clearly flagged):** the calendar's **rotation-projection rework** (Plan 1
  deleted the schedule generator, so `scheduled_workouts` no longer populates a future; the existing
  `/calendar` keeps working for past sessions and is reachable, but projecting the rotation forward is
  its own data-dependent piece) and the **active-session logging loop** (specs 05/06, full-stack with
  new tables). Neither is in this plan.

**Target nav (6):** Today · Workouts · Programs · Nutrition · Health · Insights. Settings moves off the
primary bar (gear in the top bar). Mobile tab bar stays 5: Today · Workouts · Programs · Nutrition ·
Insights (Health + Settings = desktop sidebar + deep links). Exercises and Body are removed as nav
destinations (folded into Workouts and Health).

---

## Task 1 — Nav consolidation (9→6) + Settings off-bar + redirects

**Files:** `src/components/layout/nav-items.ts`, `desktop-sidebar.tsx`, `mobile-tabbar.tsx`,
`top-bar.tsx`; new redirect stub `src/app/(app)/body/page.tsx` (replace with `redirect("/health")`).

- `nav-items.ts`: reduce to the 6 destinations above (drop the `Exercises` and `Body` entries; drop
  `Settings` from the primary list). Keep `Health` (now the merged surface). Mobile-visible set stays
  the 5 listed. Keep `tutorialId`s that survive.
- `top-bar.tsx`: add a **Settings gear** link (to `/settings`) beside Help, so Settings stays reachable
  off the primary nav.
- `body/page.tsx`: `import { redirect } from "next/navigation"; export default function BodyRedirect(): never { redirect("/health"); }` (the existing `/workouts/calendar` → `/calendar` redirect is the pattern).
- Leave the `/exercises` routes in place (Task 3 surfaces the library under Workouts; the routes still
  resolve, just not from nav).
- **DoD:** `pnpm typecheck` + `pnpm lint` + `pnpm build`. Commit:
  `feat(web): consolidate nav to 6 destinations, settings off-bar, /body→/health redirect`.

## Task 2 — Merge Body into Health (Metrics + Wearable)

**Files:** `src/app/(app)/health/page.tsx`; reuse `src/components/body/*`
(`weight-trend-card`, `weight-history-list`, `log-weight-sheet`) and `src/components/health/*`
(`metric-trend-card`, `reconnect-banner`) and the `useBodyMetrics`/`useBodyTrend`/`useReadinessHistory`
hooks.

- Restructure Health into two clearly-labeled sections per `04-page-specs.md` "Health":
  - **Metrics** (formerly Body): current weight / weekly change / last-logged tiles, the weight trend
    card, the weight history list, and the Log-weight action.
  - **Wearable** (existing Health): Steps / Sleep / Resting HR / HRV tiles + the four trend cards, with
    one connection card/status (the Fitbit→Google Health connection lives here).
- `Reveal`/`RevealGroup` the two sections; `.page-shell` + fluid spacing; verify phone/tablet/desktop.
- **DoD:** `pnpm typecheck` + `pnpm lint`. Commit:
  `feat(web): merge Body metrics into Health (Metrics + Wearable sections)`.

## Task 3 — Workouts hub (Train + Library, single calendar reachable)

**Files:** `src/app/(app)/workouts/page.tsx` (rework into a hub); reuse the exercise library from
`src/app/(app)/exercises/page.tsx` (extract its body into a reusable `ExerciseLibrary` component under
`src/components/exercise/` if not already, so both `/exercises` and the Workouts hub can render it);
`src/lib/hooks/programs.ts` `usePosition`.

- The Workouts landing becomes a **hub** with sections/tabs (editorial, responsive):
  - **Train**: a "today's session" card from the active program's **rotation position**
    (`usePosition(activeProgramId)`) — current slot name, exercise summary, and a Start that creates a
    session (freestyle empty session via the existing `useCreateEmptySession` for now; the
    pre-filled-from-slot start is part of the deferred logging loop). Below it, the **recent history**
    list (the existing `useSessionHistory` grouping). A **Calendar** link to `/calendar` and an
    **Exercises** entry stay reachable.
  - **Library**: render the `ExerciseLibrary` (search + muscle/equipment filters + grid; cards link to
    `/exercises/{id}`). This folds the desktop-only Exercises page into Workouts so mobile reaches it too.
- Apply `RevealGroup` on load; `.page-shell` + fluid spacing; tablet/mid-window verified.
- `/exercises` keeps working (renders the same `ExerciseLibrary`); exercise detail unchanged.
- **DoD:** `pnpm typecheck` + `pnpm lint`. Commit:
  `feat(web): Workouts hub — Train (rotation position + history) + folded exercise library`.

## Task 4 — Responsive + motion polish, full green

**Files:** the touched surfaces + any CSS.
- Sweep the merged Health and Workouts hub for breathing room at mobile / tablet (768–1024) / desktop;
  confirm reduced-motion paths; confirm the 6-item sidebar + 5-item tab bar render correctly and the
  `/body` redirect works.
- **DoD (final):** `pnpm typecheck` + `pnpm lint` + `pnpm test` + `pnpm build` all green. Commit:
  `feat(web): IA + Workouts hub responsive/motion polish`.

## Visual verification (orchestrator)
Restart the dev servers, screenshot the 6-item nav (desktop sidebar + mobile tab bar), the merged
Health (Metrics + Wearable), and the Workouts hub (Train + Library) at 390 / 834 / 1440, light + dark.

## Acceptance (`03 §4` + Workouts bullets of `04`)
- [ ] Nav shows six destinations; mobile tab bar shows five; Settings reachable via the top bar.
- [ ] `/body` redirects to `/health`; Health shows merged Metrics + Wearable with one connection.
- [ ] Exercises library + detail reachable under Workouts (and on mobile).
- [ ] Workouts hub shows the rotation-driven today card + recent history + library.
- [ ] typecheck/lint/test/build green; light + dark verified at phone/tablet/desktop.

## Out of scope (next phases)
- Calendar rotation-projection rework (data-dependent; the date-pinned `/calendar` stays for now).
- Active-session logging loop + structured work (specs 05/06, full-stack).
- iOS port of these surfaces (after the web shape settles, per the per-surface pattern).
