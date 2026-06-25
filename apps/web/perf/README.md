# Performance test suite

Catches the front-end performance regressions found in the June 2026 audit:
route-transition animations, unvirtualized lists, missing memoization, query
waterfalls, and heavy route bundles. Nothing here measured before; this is the
baseline.

## Philosophy: budgets as ratchets

Every check is a budget pinned at (or near) today's baseline in `budgets.json`, so
the suite is green now and any regression fails. As the fixes land (see
`tasks/redesign/` is unrelated; perf fixes are tracked separately), tighten the
numbers in `budgets.json` to lock each win in. `budgets.json` is the single source
of truth shared by all three layers.

## The three layers

### 1. Static guardrails (Vitest, no browser)

```
pnpm perf          # runs tests/perf
```

- `client-component-budget.test.ts` caps "use client" files, client route pages,
  client layouts, and motion-importing files. Fewer client components means less
  hydration and more server rendering.
- `render-count.test.tsx` uses the React Profiler to cap how often a hot leaf
  (`SetRow`) re-renders on unrelated parent updates. Memoizing it drops the count
  to 0; then tighten the budget.

These also run as part of `pnpm test` (they match the `tests/**` glob).

### 2. Bundle-size budgets (post-build, no browser)

```
pnpm build && pnpm perf:bundle
```

`scripts/check-bundle-budgets.mjs` reads `.next/app-build-manifest.json` and
compares each route's first-load client JS (gzipped) to `bundleKBGzip` in
`budgets.json`. Catches a heavy library (for example recharts) being pulled into a
route synchronously. The current budgets are generous placeholders; run one real
build, read the printed table, and tighten them to the measured baseline.

### 3. Runtime web-vitals + transitions (Playwright, needs the app running)

```
# in two terminals:
cd apps/api && uv run uvicorn app.main:app --port 8000
cd apps/web && pnpm dev
# then:
pnpm perf:e2e
```

`e2e/perf/web-vitals.perf.spec.ts` signs in via the dev auth endpoint (same as the
functional e2e), then per route measures LCP and CLS, and for client-side
transitions measures the transition time and the worst long task that blocks the
main thread during it. This is the layer that directly tests the "transitions feel
slow" complaint. Budgets are in `webVitals` in `budgets.json`.

## Updating budgets after a fix

1. Make the perf fix (for example remove the route-transition `Reveal`, or wrap a
   component in `React.memo`).
2. Re-run the relevant layer and read the new numbers.
3. Lower the matching value in `budgets.json` so the improvement cannot regress.
