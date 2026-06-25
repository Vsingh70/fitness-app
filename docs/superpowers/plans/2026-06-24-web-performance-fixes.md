# Web Performance Fixes (driven by the perf suite)

> Built by the build-test-fix loop: Builder = `web-dev`, Checker = `qa-verifier`
> (`pnpm typecheck` / `pnpm lint` / `pnpm test` / `pnpm build`, plus the perf suite below).
> Independent of the redesign vertical slices, but Tasks 1 and 3 touch the motion system
> introduced in `2026-06-23-programs-responsive-motion-web.md`, so land this after that plan
> (or coordinate the shared files). Run one task at a time per the loop stop rules in
> `CLAUDE.md`.

**Goal:** Remove the front-end performance regressions found in the June 2026 audit so the
web app stops feeling slow, especially route transitions, and lock each win in with the
performance suite under `apps/web/perf/`.

**Scope decisions (locked):**

- **In:** kill the route-transition animation, memoize hot leaves, virtualize long lists,
  fix query waterfalls, memoize in-render sorts, reduce client-component sprawl, code-split
  heavy routes, wire the suite into CI.
- **Out:** any redesign feature work (covered by the other plans), iOS, backend changes.
- **Hard rule (from `CLAUDE.md`):** never weaken, delete, skip, or loosen a test, type, or
  lint rule to reach green. For the perf budgets in `perf/budgets.json` this means budgets
  may only be **tightened** (lowered) as fixes land. Raising a budget to make a check pass
  counts as loosening and is forbidden. Fix the code.

---

## The performance suite (how to run it)

The suite lives in `apps/web/`. It is a set of budgets pinned at the June 2026 baseline, so
it is green today and any regression fails. Three layers:

1. **Static guardrails (Vitest, no browser).** Caps client-component sprawl and hot-leaf
   re-renders.
   - `apps/web/tests/perf/client-component-budget.test.ts`
   - `apps/web/tests/perf/render-count.test.tsx`
   - Run: `cd apps/web && npx vitest run tests/perf` (also runs inside `pnpm test`).
2. **Bundle-size budgets (post-build, no browser).** Per-route first-load JS (gzipped).
   - `apps/web/scripts/check-bundle-budgets.mjs`
   - Run: `cd apps/web && pnpm build && node scripts/check-bundle-budgets.mjs`
3. **Runtime web-vitals + transitions (Playwright, needs the app running).** LCP, CLS,
   route-transition time, and main-thread long tasks during a transition.
   - `apps/web/e2e/perf/web-vitals.perf.spec.ts`
   - Run (two terminals): `cd apps/api && uv run uvicorn app.main:app --port 8000`, then
     `cd apps/web && pnpm dev`, then `cd apps/web && npx playwright test e2e/perf`.

Budgets are the single source of truth in `apps/web/perf/budgets.json`. Full notes in
`apps/web/perf/README.md`.

Optional convenience scripts (add to `apps/web/package.json` `scripts` if desired):
`"perf": "vitest run tests/perf"`, `"perf:bundle": "node scripts/check-bundle-budgets.mjs"`,
`"perf:e2e": "playwright test e2e/perf"`.

Environment notes: the Vitest layer needs `node_modules` installed for the host platform
(Vitest 4 ships a native binary). The bundle layer needs a prior `pnpm build`. The Playwright
layer needs the API and web dev server running, same as the existing e2e.

## Budget ratchet workflow (do this in every task)

1. Make the fix.
2. Re-run the relevant suite layer and read the new numbers.
3. Lower the matching value in `perf/budgets.json` to just above the new baseline so the win
   cannot regress.
4. Confirm the suite is green at the tighter budget, then commit the code and the budget
   change together.

---

## Findings (context for the tasks)

From the audit, in priority order:

1. **Route-transition animation.** `app/(app)/layout.tsx` wraps all page content in
   `<Reveal key={pathname}>`, so every navigation plays a ~300ms fade-and-lift. This is most
   of the felt slowness. `Pressable` runs hover/tap motion on nearly every button, and
   `RevealGroup` staggers fade-ins on home, calendar, and nutrition, delaying first paint.
2. **Unvirtualized long lists** (8): meal list, exercise history scatter (up to 1000 points),
   calendar projection (nested loops), workout history, ingredient search, program library.
3. **No `React.memo` anywhere** plus inline arrow handlers, so hot leaves (SetRow, MealRow,
   FoodRow, ExerciseCard) re-render on unrelated parent updates.
4. **Query waterfalls** on workout detail, calendar, and nutrition day (3 to 4 dependent
   fetches each).
5. **In-render sorts/maps** not memoized (home, workout history, health, exercise scatter,
   analytics).
6. **Heavy routes / client sprawl:** 22 of 28 route pages are `"use client"`; recharts on the
   chart routes.

---

## Phase 1 — Quick wins

### Task 1 — Remove the route-transition animation

**Files:** `apps/web/src/app/(app)/layout.tsx` (and the motion primitives in
`apps/web/src/components/motion/` if they need a no-op path).

- Stop wrapping `{children}` in `<Reveal key={pathname}>`. Render children directly so a
  navigation paints immediately. Keep per-section `RevealGroup` reveals only where they are a
  single deliberate page-load moment, and pass `initial={false}` (or defer to a post-paint
  effect) so they never delay LCP.
- Coordinate with `2026-06-23-programs-responsive-motion-web.md`, which owns the motion system;
  this task changes how it is applied at the route boundary, not its primitives.
- **DoD:** `npx playwright test e2e/perf` transition assertions pass; lower
  `webVitals.routeTransitionMs` and `webVitals.longTaskDuringTransitionMsMax` in
  `perf/budgets.json` to the new measured values. `pnpm typecheck`/`lint`/`test`/`build` green.
  Verify visually that navigation still feels intentional, not jarring.

### Task 2 — Memoize hot leaf components

**Files:** `apps/web/src/components/workouts/set-row.tsx`, `exercise-card.tsx`,
`apps/web/src/components/nutrition/meal-list.tsx` (MealRow),
`apps/web/src/components/nutrition/ingredient-picker.tsx` (FoodRow); their parents for prop
stability.

- Wrap each in `React.memo`. Stabilize the props they receive: replace inline
  `onClick={() => ...}` and inline object/array literals in the parents with `useCallback` /
  `useMemo` so the memo can bail out.
- Extend `tests/perf/render-count.test.tsx` with the same Profiler pattern for MealRow and
  FoodRow.
- **DoD:** render-count tests pass at a tightened budget (SetRow `render.setRowUnrelatedRerendersMax`
  drops toward 0; add budgets for the others). `pnpm typecheck`/`lint`/`test`/`build` green.

### Task 3 — Gate always-on button motion

**Files:** `apps/web/src/components/motion/Pressable.tsx` and its call sites.

- Make hover motion cheap or opt-in: prefer a CSS hover cue over a JS `whileHover` transform on
  every button, and keep `whileTap` only where it adds feedback. Honor reduced motion (already
  wired) and avoid layout-animating large trees.
- **DoD:** `static.motionImportFilesMax` holds (no new motion files); the transition long-task
  budget from Task 1 still passes. Green checks. Visual check on a dense list screen.

---

## Phase 2 — Medium impact

### Task 4 — Virtualize long lists

**Files:** `apps/web/src/components/nutrition/meal-list.tsx`,
`apps/web/src/app/(app)/exercises/[id]/page.tsx` (scatter),
`apps/web/src/app/(app)/calendar/page.tsx`, `apps/web/src/app/(app)/workouts/page.tsx`,
`apps/web/src/components/nutrition/ingredient-picker.tsx`,
`apps/web/src/components/programs/program-library.tsx`. New dep: `@tanstack/react-virtual`.

- Window lists that can exceed ~30 rows. For the exercise scatter, cap or virtualize the
  rendered points. For the calendar, render only the current and next couple of microcycles.
- **DoD:** lists scroll without rendering every row; `pnpm typecheck`/`lint`/`test`/`build`
  green. Add a test asserting a large list mounts a bounded number of row nodes.

### Task 5 — Fix query waterfalls

**Files:** `apps/web/src/app/(app)/workouts/[id]/page.tsx`,
`apps/web/src/app/(app)/calendar/page.tsx`,
`apps/web/src/components/nutrition/nutrition-day.tsx`; relevant hooks in `src/lib/hooks/`.

- Replace serial dependent queries with parallel fetches (`useQueries`) where possible, and add
  `placeholderData` / `keepPreviousData` so dependent steps do not blank the screen. Use stable
  array query keys rather than `ids.join(",")` strings.
- **DoD:** no behavior change; `pnpm typecheck`/`lint`/`test`/`build` green. Verify the heavy
  pages paint content without a visible multi-step blank.

### Task 6 — Memoize in-render computation

**Files:** `apps/web/src/app/(app)/page.tsx`, `workouts/page.tsx`, `health/page.tsx`,
`exercises/[id]/page.tsx`, `analytics/page.tsx`.

- Wrap `.sort()/.map()/.filter()` chains in `useMemo`; use `toSorted()` instead of mutating
  `.sort()`. Move heavy transforms into hooks or utils.
- **DoD:** `pnpm typecheck`/`lint`/`test`/`build` green.

---

## Phase 3 — Architecture

### Task 7 — Reduce client components

**Files:** route pages under `apps/web/src/app/(app)/` that are `"use client"` only for data
fetching or layout.

- Convert route pages to server components where feasible, pushing `"use client"` down to the
  interactive islands. Target the read-mostly routes first (analytics, health, exercise detail).
- **DoD:** lower `static.clientRoutePagesMax` (and `useClientFilesMax`) in `perf/budgets.json`
  to the new counts; `tests/perf/client-component-budget.test.ts` passes at the tighter ceiling.
  `pnpm typecheck`/`lint`/`test`/`build` green; app works in light and dark.

### Task 8 — Code-split heavy routes and confirm charts are lazy

**Files:** `apps/web/src/app/(app)/settings/page.tsx`,
`apps/web/src/components/programs/program-builder.tsx`, chart components in
`apps/web/src/components/charts/` and `nutrition/`.

- Split large components with `next/dynamic` (modals, editor panels), and confirm recharts is
  only loaded behind a dynamic boundary on the chart routes.
- **DoD:** run `pnpm build && node scripts/check-bundle-budgets.mjs`; lower the affected route
  budgets in `perf/budgets.json` to the new measured sizes. Green checks.

### Task 9 — Wire the suite into CI

**Files:** the web CI workflow under `.github/workflows/`, optionally `apps/web/package.json`
scripts.

- Run the static layer in the existing web check job (`pnpm test` already includes
  `tests/perf`). Add a post-build step running `node scripts/check-bundle-budgets.mjs`. Optionally
  add the Playwright perf job behind the compose-up step the e2e already needs.
- **DoD:** CI fails on a perf budget regression; the job is green on `main` at current budgets.

---

## Loop stop rules (from CLAUDE.md)

Stop and report when: all checks in the task DoD pass (success, with checker output as proof);
5 cycles are used; the same failure repeats twice; or a fix makes a previously passing check
fail. Never report success without checker output from the final cycle. Never loosen a budget,
test, type, or lint rule to go green; tighten budgets only.
