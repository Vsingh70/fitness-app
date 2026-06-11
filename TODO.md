# Backend + ops punch list

Everything left to finish before this app is operational and feature-complete.
Grouped by track. Within each group, ordered by priority. Effort is a rough
"how long if I sit down and do nothing else" estimate.

Track legend:
- **API** — backend code / migrations
- **DEPLOY** — infrastructure, CI/CD, secrets
- **OBS** — observability (metrics, traces, alerts)
- **WEB** — frontend (called out where it blocks backend testing)
- **iOS** — deferred, listed for completeness
- **OPS** — manual, external systems, accounts

---

## P0 — blocking real-world use

### DEPLOY-1. Stand up the Hetzner VPS [~1 day]
- Provision a CX22 (or equivalent) in `eu-central` or `us-east`.
- Run `ansible-playbook -i infra/ansible/inventory.ini infra/ansible/site.yml`.
- Verify roles applied: base hardening, docker, postgres, redis, ollama,
  caddy, monitoring (node_exporter, promtail).
- Copy `app-compose.yml.example` to `/etc/gymapp/app-compose.yml` on the
  host and fill secrets.
- Pull a first image manually to validate registry auth.
- **Files:** `infra/ansible/`, `infra/ansible/site.yml`.

### DEPLOY-2. Configure all production secrets and env [~2 hours]
GitHub Actions repo secrets:
- `DEPLOY_HOST` — VPS IP/hostname
- `DEPLOY_USER` — `ops`
- `DEPLOY_SSH_KEY` — private key for the deploy user
- `DISCORD_WEBHOOK_URL` — for deploy success/failure pings
- `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY` — Backblaze
- iOS bundle secrets (see `apps/ios/README.md`) — deferred with iOS

GitHub Actions repo variables:
- `APP_DOMAIN` — e.g. `gym.example.com`
- `DEPLOY_ENABLED=true` — flip this only after the host accepts SSH

On the VPS (`/etc/gymapp/app.env`):
- `JWT_SECRET` — 64-byte hex
- `APPLE_BUNDLE_IDS`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`
- `GOOGLE_CLIENT_IDS` — comma-separated allowed audiences
- `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET`, `FITBIT_VERIFY_TOKEN`
- `METRICS_TOKEN` — gates `/metrics` endpoint
- `OLLAMA_BASE_URL=http://host.docker.internal:11434` (or the host IP)
- `OTEL_EXPORTER_OTLP_ENDPOINT` — Grafana Cloud OTLP URL, optional but needed for traces
- `OFF_USER_AGENT` — your contact for OpenFoodFacts politeness header

### DEPLOY-3. Wire Vercel deploy [~1 hour]
- Connect the GitHub repo to a new Vercel project.
- Set root directory to `apps/web`.
- Build command: `pnpm install --frozen-lockfile && pnpm openapi:generate && pnpm build`.
- Set `NEXT_PUBLIC_API_URL` to the VPS URL.
- Pull `vercel.json` settings (auto-detected on connect).
- **Files:** `apps/web/vercel.json`.

### DEPLOY-4. First end-to-end deploy and smoke test [~2 hours]
- Push a no-op commit to `main`.
- Confirm `api-deploy.yml` builds → pushes → SSHes → migrates → swaps.
- `curl https://<APP_DOMAIN>/v1/health/ready` → 200.
- `curl https://<APP_DOMAIN>/v1/auth/dev` (only if `ENV != prod`) → JWT.
- Verify `gymapp-app-rollback previous` works on a deliberate rollback.
- **Files:** `infra/scripts/app-deploy.sh`, `infra/scripts/app-rollback.sh`.

---

## P1 — small backend fixes that should ship before opening the app to users

### API-1. Wire Ollama metric emit sites [~30 min]
Counter is registered but never incremented. Add to
`apps/api/app/clients/ollama.py` around each request:
```python
OLLAMA_REQUESTS_TOTAL.labels(model=model, kind=kind, outcome=outcome).inc()
OLLAMA_REQUEST_DURATION_SECONDS.labels(model=model, kind=kind).observe(elapsed)
```
Outcomes: `success`, `error`, `timeout`. Kinds: `chat`, `vision`, `embed`.
- **Files:** [apps/api/app/clients/ollama.py](apps/api/app/clients/ollama.py),
  [apps/api/app/observability/metrics.py:40](apps/api/app/observability/metrics.py#L40).

### API-2. Wire Fitbit metric emit sites [~30 min]
Same pattern as Ollama. In `apps/api/app/services/fitbit_sync.py`,
increment around the sync and push paths:
```python
FITBIT_SYNC_TOTAL.labels(kind=kind, outcome=outcome).inc()
```
Kinds: `daily`, `webhook`, `push_workout`, `disconnect`.
- **Files:** [apps/api/app/services/fitbit_sync.py](apps/api/app/services/fitbit_sync.py),
  [apps/api/app/services/fitbit_push.py](apps/api/app/services/fitbit_push.py),
  [apps/api/app/observability/metrics.py:47](apps/api/app/observability/metrics.py#L47).

### API-3. Support `JWT_SECRET_PREVIOUS` for zero-downtime secret rotation [~1 hour]
Today the verifier only checks one secret, so rotation logs everyone out.
- Add `JWT_SECRET_PREVIOUS` to settings.
- In `verify_access_token`, try the current secret first, fall back to the
  previous if set, log a warning when a token verifies against the previous.
- Add a unit test covering both branches.
- **Files:** [apps/api/app/services/auth.py](apps/api/app/services/auth.py),
  [apps/api/app/config.py](apps/api/app/config.py),
  [apps/api/tests/test_auth.py](apps/api/tests/test_auth.py).

### API-4. Workouts router (in progress, uncommitted) [~half day]
Uncommitted changes on disk introduce a workouts feature. Decide whether
to land or revert:
- `apps/api/app/models/workout.py`
- `apps/api/app/models/exercise_progression.py`
- `apps/api/app/models/idempotency_key.py`
- `apps/api/app/routers/workouts.py`
- `apps/api/app/schemas/workout.py`
- `apps/api/app/services/idempotency.py`
- `apps/api/app/services/workouts.py`
- `apps/api/alembic/versions/20260525_0004_workouts.py`
- `apps/api/tests/test_workouts_api.py`

If keeping: run `uv run pytest`, ensure migration is reversible, regenerate
the OpenAPI spec via `uv run python -m scripts.export_openapi >
../../packages/openapi/openapi.json`, commit.
If discarding: `git checkout .` (confirm intent first; this is destructive).

### OBS-1. Implement "100% sample on errors" tracing override [~half day]
Current sampler is `ParentBased(TraceIdRatioBased(0.1))`. We want to also
sample every span whose status is `ERROR`.
- Write a custom `Sampler` that wraps `TraceIdRatioBased` and inspects
  attributes / status to force-sample errors.
- Wire it into `tracing.py`.
- Add a test that simulates an erroring span and asserts it sampled.
- **Files:** [apps/api/app/observability/tracing.py:38](apps/api/app/observability/tracing.py#L38).

### OBS-2. Grafana Cloud + Discord alert wiring [~1 hour]
Alert rules and dashboards are in `infra/grafana/` but the operator
needs to:
- Create a free Grafana Cloud account.
- Import dashboards from `infra/grafana/dashboards/`.
- Import alerts from `infra/grafana/alerts/`.
- Point alert delivery at the `DISCORD_WEBHOOK_URL`.
- Verify with a deliberate alert (e.g. set `BackupNotCompleted` window to
  `1m` to fire it, then revert).
- **Files:** `infra/grafana/`.

### OBS-3. BetterStack synthetic monitor [~30 min]
Template exists; finish it.
- Create a BetterStack account.
- Import the monitor template from `infra/synthetic/`.
- Target `https://<APP_DOMAIN>/v1/health/ready` and `https://<APP_DOMAIN>/v1/health/live`.
- Pipe alerts to the same Discord webhook.
- **Files:** `infra/synthetic/`.

---

## P2 — feature gaps

### API-5. Recommendation auto-application audit [~1 hour]
04.01 auto-applies linear/double progression. Confirm the daily cron
ran at least once on real data and check `recommendations` rows are
both produced and consumed. Add a backend test verifying
"applied_at" is set after the cron path runs.

### API-6. Insight TTL / dismissal [~half day]
`analytics_insights` rows accumulate forever. Add:
- `dismissed_at` column + endpoint `PATCH /v1/insights/{id}` to set it.
- A 30-day default TTL on stagnation insights (the LLM-rationale ones
  cost real Ollama time to regenerate, so keep those longer).
- An index on `(user_id, dismissed_at IS NULL, created_at DESC)` for the
  Today screen query.

### API-7. Soft-delete cleanup job [~half day]
`workout_sessions`, `programs`, `meals` use soft delete. Add a nightly
ARQ job that hard-deletes rows whose `deleted_at` is older than 90 days,
emits a metric, and writes a structlog summary.

### API-8. Rate-limit hard ceilings [~1 hour]
`rate_limit.py` has a Redis-backed sliding window. Verify limits match
spec (600/min user, 30/min IP for auth, 60/hour user for AI). Add a
test that exercises each tier.

### API-9. Idempotency key TTL job [~1 hour]
`idempotency_keys` table grows monotonically. Add a daily job that drops
rows older than 7 days. Index on `created_at` if missing.

### API-10. Apple/Google JWK cache hardening [~1 hour]
OIDC verification fetches JWKs per request unless cached. Confirm cache
TTL is sensible (10 min) and there's no thundering herd if cache misses.
Add a stale-while-revalidate path so a JWK fetch failure during rotation
keeps the API up on the previous keyset.

### API-11. Meal photo cleanup [~1 hour]
Photos stored under `/var/lib/gymapp/meal-photos` are synced to B2 but
never deleted locally. Add an opt-in cleanup job that drops local copies
older than 30 days (rclone keeps the remote copy).

---

## P3 — observability + ops polish

### OBS-4. Tracing instrumentation per request path [~half day]
OpenTelemetry SDK is wired but spans are bare. Add custom spans around:
- Ollama calls (`ai.ollama.chat`, `ai.ollama.vision`).
- DB transactions in writeback paths (`db.tx.<table>`).
- Fitbit OAuth + sync (`fitbit.oauth`, `fitbit.sync.daily`, `fitbit.sync.webhook`).
- Background ARQ jobs (`arq.<job_name>`).
Set span attributes for `user_id` (hash, not raw) and `request_id`.

### OBS-5. Loki log shipping label hygiene [~1 hour]
Promtail is configured but verify labels don't include high-cardinality
fields (no `user_id`, no `request_id` as labels — those go in the line
content). Run `logcli labels` against Loki to confirm.

### OBS-6. SLO dashboard [~1 hour]
Add a dashboard with:
- API availability over 28d (target 99.5%).
- p99 latency on `/v1/workouts/sessions` and `/v1/foods/search` (target < 500ms).
- Background job lag (target < 5 min).
Burn-rate alerts at 2h and 24h windows.

### OPS-1. Backup restore drill [~1 hour]
Run `infra/scripts/pg-restore.sh` against a *staging* DB (or a throwaway
container) to verify the daily backup actually restores. Document the
elapsed time in `docs/runbooks/restore.md`.

### OPS-2. Secret rotation drill [~half day]
Following `docs/runbooks/rotate-secrets.md`:
- Rotate `JWT_SECRET` (needs API-3 first, otherwise logs everyone out).
- Rotate `METRICS_TOKEN` and verify Grafana/Prometheus scraping still works.
- Rotate the deploy SSH key and verify CI still ships.

### OPS-3. Domain + Caddy TLS verify [~30 min]
After DEPLOY-1, point DNS at the VPS, wait for Caddy to issue the cert,
verify HSTS + cert chain with `curl -vk https://<APP_DOMAIN>/`.

### OPS-4. Discord channel for alerts [~10 min]
Create a private "gymapp-alerts" channel. Save the webhook URL into
GitHub Actions secrets and Grafana.

### OPS-5. iOS distribution accounts (deferred until iOS work) [~2 hours]
- Apple Developer Program enrollment ($99/yr).
- App Store Connect app record.
- TestFlight group for buddies.
- Match repo for fastlane signing.

---

## P4 — feature work that's API-shaped, surface in the spec

These are tasks that don't have their own spec file yet but the data
model already supports. Worth scoping before iOS lands.

### API-12. Personal-records timeline endpoint [~1 day]
`GET /v1/me/prs` returning paginated PR events across all exercises with
e1RM delta, date, session link. Backed by existing `prs` table.

### API-13. Body-metrics trend endpoint [~half day]
Series for weight, body fat %, neck/waist/hip across N weeks, with
moving average. Backed by `body_metrics`. Today the table is written
but no read endpoint surfaces it.

### API-14. Export endpoint [~half day]
`GET /v1/me/export` returning the user's full data as a JSON bundle
(sessions, sets, meals, body metrics, programs). Compliance + portability.

### API-15. Quick-log workout from history [~1 day]
"Repeat last workout" endpoint. Takes a `workout_session_id` and clones
it with today's date, blank set entries that prefill last performance.

---

## iOS — all deferred [~2 weeks of work once Xcode is available]

These are spec'd in `tasks/08-ios/` but cannot start without a Mac with
Xcode 16. Listed for completeness.

- **iOS-1** `08.01` skeleton (`tasks/08-ios/01-ios-skeleton.md`)
- **iOS-2** `08.02` tracking
- **iOS-3** `08.03` programming
- **iOS-4** `08.04` analytics
- **iOS-5** `08.05` nutrition

iOS CD already exists: [`.github/workflows/ios-release.yml`](.github/workflows/ios-release.yml)
and [`apps/ios/fastlane/Fastfile`](apps/ios/fastlane/Fastfile).

An **editorial-system iOS guide** is ready at
[tasks/claude-code-editorial-ios.md](tasks/claude-code-editorial-ios.md):
asset-catalog color sets, `Font.system(design: .serif)` setup, editorial
component recipes (Card, Kicker, underline tabs, ink primary button,
heat ramp). Apply it inside `08.01` once the SwiftUI skeleton compiles.

---

## Web UI — editorial design landed, screens still to build [~2 weeks]

The **editorial design system is implemented** (tokens, primitives,
layout, charts, sign-in, workouts shell). HTML prototypes for every
screen live at [tasks/web/](tasks/web/) and are the per-screen visual
source of truth. Per-screen build order, prototype on the left:

### WEB-1. Today screen ✅ shipped (2026-06-01)
Prototype: [tasks/web/today.html](tasks/web/today.html). Page:
[apps/web/src/app/(app)/page.tsx](apps/web/src/app/(app)/page.tsx).
Shipped:
- Readiness tile (`ReadinessTile`) with band-tinted ring, score + band copy.
- Scheduled-workout hero (`ScheduledHero`) with day name, exercise count,
  Deload pill, week badge, Start CTA.
- Nutrition strip (`NutritionStrip`) — kcal ring + 4 macro bars + Log/Full-day.
- Recommendation cards (`RecommendationCard`) — kind kicker, serif title,
  rationale, confidence pips, "Why?" / "Apply to today" CTA.
- Week stats row (`StatTile` × 3) — sessions this week / last logged / active.
- Recent sessions list with "Start empty workout" demoted to footer.
- Hooks at [apps/web/src/lib/hooks/today.ts](apps/web/src/lib/hooks/today.ts)
  pulling `/v1/readiness/today`, `/v1/recommendations`, `/v1/nutrition/day`,
  `/v1/nutrition/targets`, `/v1/scheduled-workouts`.

Follow-ups deferred to later passes:
- Drag-reorderable Fitbit stat carousel (visual polish; `today.html` shows it).
- Mini trend sparklines on recommendation cards.
- Live "Apply to today" wiring (currently a no-op button).

### WEB-2. Active workout polish ✅ shipped (2026-06-01)
Prototype: [tasks/web/workout-active.html](tasks/web/workout-active.html).
Page: [(app)/workouts/[id]/page.tsx](apps/web/src/app/(app)/workouts/%5Bid%5D/page.tsx).
Shipped:
- **ExerciseRail** ([components/workouts/exercise-rail.tsx](apps/web/src/components/workouts/exercise-rail.tsx))
  — sticky pill nav across the top, active = clay fill, complete = sage,
  click scrolls the matching exercise card into view.
- **PlateMathStrip** ([components/workouts/plate-math.tsx](apps/web/src/components/workouts/plate-math.tsx))
  — visual plate diagram + "x kg · y per side" copy, only renders for
  `equipment=barbell` + `tracking_type=weight_reps`. 20 kg bar baseline.
- **FloatingRestBar** ([components/workouts/floating-rest-bar.tsx](apps/web/src/components/workouts/floating-rest-bar.tsx))
  — fixed-bottom card with a countdown ring, +30s (computed internally
  against `effectiveTotal` so extension actually adds time), Skip, idle
  state with Clock icon and "Start rest" CTA. The one allowed shadow.
- **KeyboardShortcutsSheet** ([components/workouts/keyboard-shortcuts.tsx](apps/web/src/components/workouts/keyboard-shortcuts.tsx))
  — `?` toggles a modal cheat sheet (j/k/n/e/r/⌘↵/Esc). The
  `KeyboardShortcuts` hook now drives navigation as well as adds.
- **NextUpPreview** ([components/workouts/next-up-preview.tsx](apps/web/src/components/workouts/next-up-preview.tsx))
  — muted card under the active exercise with "Up next · name · Skip ahead →".
- **Editorial polish** on the page itself: "In progress" / "Finished"
  kicker above the serif session title, top-right `?` pill button, serif
  session timer below the title, larger bottom padding so the floating
  rest bar doesn't overlap content.

Deferred follow-ups:
- Per-set "current"/"completed"/"synced" state — needs the SetRow data
  model to track completion separately from "saved to server", which is
  a non-trivial refactor of the offline queue contract.
- RPE popover on each set row (prototype shows a 6→9.5 grid + Clear).
- Drag-to-reorder exercises in the rail.
- `Tab` and `⌘↵` shortcuts inside the set row (currently global only).

### WEB-3. Workout summary ✅ shipped (2026-06-01)
Prototype: [tasks/web/workout-summary.html](tasks/web/workout-summary.html).
Page: [(app)/workouts/[id]/summary/page.tsx](apps/web/src/app/(app)/workouts/%5Bid%5D/summary/page.tsx).
Shipped:
- **PrBanner** ([components/workouts/summary/pr-banner.tsx](apps/web/src/components/workouts/summary/pr-banner.tsx))
  — mustard "PR" mark + radial-gradient backdrop, serif headline,
  per-PR list (weight × reps + Brzycki e1RM), deep-link to exercise
  page when exactly one PR.
- **Stat tile grid** — Duration, Working sets, Volume (kg, comma-formatted),
  Avg RPE — all editorial top-rule + serif figure.
- **SetByExerciseTable** ([components/workouts/summary/set-by-exercise-table.tsx](apps/web/src/components/workouts/summary/set-by-exercise-table.tsx))
  — hairline table grouped by exercise (only first row shows name),
  warmup rows tinted tertiary, PR rows tinted mustard with a 3 px
  mustard left border, RPE column.
- **SessionVolumeByMuscle** ([components/workouts/summary/session-volume-by-muscle.tsx](apps/web/src/components/workouts/summary/session-volume-by-muscle.tsx))
  — primary 1.0 / secondary 0.5 weighted bars for muscles trained
  this session.
- **NextSessionRecs** ([components/workouts/summary/next-session-recs.tsx](apps/web/src/components/workouts/summary/next-session-recs.tsx))
  — recommendation cards filtered to exercises this session touched,
  rendered in a 2×2 grid with kicker + serif title + rationale.
- **Editorial header**: "Finished" kicker + serif title + friendly
  date copy, Edit-session secondary + Done primary.
- **Session notes** card if `s.notes` is set.

Deferred follow-ups:
- "vs typical Push A" comparison bars on the volume card — needs a
  rolling-history endpoint (not yet built).
- "Share session" button (prototype has it; product decision pending).
- "Mark as deload" + "Delete session" footer actions.

### WEB-4. Per-exercise page ✅ shipped (2026-06-01)
Prototype: [tasks/web/exercise.html](tasks/web/exercise.html). Page:
[(app)/exercises/[id]/page.tsx](apps/web/src/app/(app)/exercises/%5Bid%5D/page.tsx).
Shipped:
- **Migrated to server-side analytics endpoint.** Old page walked
  every workout session and aggregated client-side; new page calls
  `GET /v1/analytics/exercises/{id}?window=…` once.
  ([lib/api/analytics.ts](apps/web/src/lib/api/analytics.ts),
  [lib/hooks/analytics.ts](apps/web/src/lib/hooks/analytics.ts)).
- **ExerciseHero** ([components/exercise/exercise-hero.tsx](apps/web/src/components/exercise/exercise-hero.tsx))
  — radial clay-soft backdrop, kicker "Compound · barbell" copy, serif
  title, primary-muscle chip in clay + secondaries in hairline.
- **PredictedNextStrip** ([components/exercise/predicted-next-strip.tsx](apps/web/src/components/exercise/predicted-next-strip.tsx))
  — `bg-accent-soft` callout reading the `predicted_next_session`
  shape (kind kicker, summarized title, rationale, mono source tag).
- **PrTileRow** ([components/exercise/pr-tile-row.tsx](apps/web/src/components/exercise/pr-tile-row.tsx))
  — 4 editorial tiles: Best e1RM, Heaviest, Top reps @ best, Last seen.
- **UnderlineTabs** ([components/ui/tabs.tsx](apps/web/src/components/ui/tabs.tsx))
  — extracted as a reusable primitive (was inlined in 3 places).
- **Window picker** — hairline outline chips for 4w / 12w / 6mo / 1y /
  All, passed as `?window=` to the analytics endpoint.
- **Trends tab**: e1RM `TrendChart kind="line"` + working-volume bars
  side by side.
- **Sets tab**: editorial table from `set_scatter` with PR row tint +
  mustard left border, paginated 25 rows.
- **Variants tab**: `VariantsList` cards from `suggested_variants`,
  linking to each variant exercise page.

Deferred follow-ups:
- "Notes" tab (prototype shows it; needs free-text storage on the
  exercise model — not yet built).
- Compare-with overlay (the old client-side path supported it; the
  server endpoint doesn't return a second series).
- Floating "Start session with this lift" CTA from prototype.

### WEB-5. Nutrition ✅ shipped (2026-06-01)
Prototype: [tasks/web/nutrition.html](tasks/web/nutrition.html). Page:
[(app)/nutrition/page.tsx](apps/web/src/app/(app)/nutrition/page.tsx).
Shipped:
- **API + hooks** ([lib/api/nutrition.ts](apps/web/src/lib/api/nutrition.ts),
  [lib/hooks/nutrition.ts](apps/web/src/lib/hooks/nutrition.ts)) wrap
  `/v1/meals`, `/v1/meals/{id}/items`, `/v1/meal-items/{id}`,
  `/v1/foods/search`, `/v1/foods/barcode/{code}`. Mutations invalidate
  both `meals` and `nutrition.day` so the kcal ring updates live.
- **NutritionHero** ([components/nutrition/nutrition-hero.tsx](apps/web/src/components/nutrition/nutrition-hero.tsx))
  — large 180px kcal ring + 4 macro cells (Protein clay / Carbs ochre /
  Fat sage / Fiber tertiary), kcal-remaining + protein-goal footer.
- **MealSection** ([components/nutrition/meal-section.tsx](apps/web/src/components/nutrition/meal-section.tsx))
  — kicker header with meal name + time, totals (kcal / p / c / f),
  hairline item rows with delete-X, dashed "+ Add to …" CTA.
- **AddMealSheet** ([components/nutrition/add-meal-sheet.tsx](apps/web/src/components/nutrition/add-meal-sheet.tsx))
  — uses the existing `Sheet` primitive + `UnderlineTabs`. Search tab
  wired live: hits `/v1/foods/search` (2-char minimum), serif kcal/p/c/f
  per 100g. Picking a row defaults grams to the food's `serving_size_g`
  if present, else 100 g.
- **Lazy meal creation:** the page creates a `MealResponse` row on
  first add for a slot, then appends the item. Default `eaten_at` per
  slot: breakfast 08:00 / lunch 13:00 / snack 16:00 / dinner 19:00 UTC.
- **Food lookup hydration** — names + brands for existing items are
  pulled lazily via `GET /v1/foods/{id}` so item rows show real names
  not UUIDs.

Deferred follow-ups (intentionally scoped out of V1):
- **Scan tab** — needs `getUserMedia` + a barcode reader (e.g.
  `@zxing/browser`); backend `/v1/foods/barcode/{code}` is already live.
  Tab currently shows a "coming soon" callout.
- **Photo tab** — needs camera/upload UI + `/v1/meals/recognize`
  orchestration; tab shows a "coming soon" callout.
- **Grams editor** — clicking a result adds at the default serving;
  editing portion after the fact requires a `PATCH /v1/meal-items/{id}`
  hook (not yet wired).
- **Custom food creation** when search returns zero results.
- **Floating FAB** for "Add to whichever meal" prototype gesture.

### WEB-6. Insights / Analytics [~2 days]
Prototype: [tasks/web/analytics.html](tasks/web/analytics.html). Page:
[(app)/analytics/page.tsx](apps/web/src/app/(app)/analytics/page.tsx)
(stub). Build:
- Stat grid at top: workouts/week, weekly tonnage, PR count, training-week #.
- Muscle-volume heatmap (19 muscles, 4-bucket accent ramp using
  `--heat-0/1/2/3/4` already in tokens.css).
- Tonnage chart over time (`TrendChart kind="bar"`).
- Insights cards from `GET /v1/insights/weekly` — each card has severity
  band (info/notice/warning → border color) and a deep-link CTA.
- Progress-photo compare strip (deferred — body-metrics endpoint API-13
  needs to land first).

### WEB-7. Settings [~1 day]
Prototype: [tasks/web/settings.html](tasks/web/settings.html). Page:
[(app)/settings/page.tsx](apps/web/src/app/(app)/settings/page.tsx)
(account-read-only today). Build:
- **Appearance** section: theme toggle (system/light/dark) writing
  `[data-theme]` on `<html>` and `localStorage.om.theme`; accent picker
  with Clay/Slate/Teal/Ochre/Rose swatches writing `[data-accent]` and
  `localStorage.om.accent`. The CSS plumbing already exists in
  [tokens.css](apps/web/src/styles/tokens.css) — UI is the gap.
- **Units** toggle (kg/lb, m/ft) → `PATCH /v1/me`.
- **Training** section (active program selector, default rest timer).
- **Connections** (Fitbit connect/disconnect, surface last-sync time).
- **Data** section (Export → API-14 once it exists; Delete account).

### WEB-8. Calendar polish [~half day]
Prototype: [tasks/web/calendar.html](tasks/web/calendar.html). Page:
[(app)/calendar/page.tsx](apps/web/src/app/(app)/calendar/page.tsx)
(working DnD, needs visual polish).
- Convert month-grid cells to editorial flat panels (4px radius, hairline).
- Day numerals in serif tabular.
- "Today" cell: ink underline rather than accent fill.

### WEB-9. Programs polish [~half day]
Prototypes: [tasks/web/programs.html](tasks/web/programs.html),
[tasks/web/program-editor.html](tasks/web/program-editor.html),
[tasks/web/program-template.html](tasks/web/program-template.html).
Pages already exist; remaining work is to:
- Compare against the three prototypes side-by-side at 1280px.
- Volume summary card already redesigned — verify against
  `program-editor.html`'s right rail.

### WEB-10. Visual diff QA pass [~half day]
Per the editorial brief acceptance checklist:
- [ ] Start `pnpm dev`, walk every (app)/* route at 1280px and at mobile width.
- [ ] Toggle `[data-theme="dark"]` on `<html>` — verify every route legible.
- [ ] Toggle `[data-accent]` through all five — verify nothing hard-codes blue.
- [ ] Diff each route against its matching `tasks/web/*.html` prototype.
- [ ] Confirm no drop shadows anywhere except the floating rest-timer bar.

### WEB-11. Optional — branded serif via next/font [~1 hour]
The stack currently uses the system serif (Iowan / Palatino / Georgia /
New York). If a branded serif is desired, load *Spectral* or *Source
Serif 4* via `next/font` and swap `--font-serif` in
[tokens.css](apps/web/src/styles/tokens.css). Acceptable to skip — the
system stack already reads editorial.

---

## How to use this list

- Top of session, check P0 + P1 — anything not green there is the next
  thing to do.
- When picking up an API task, check `tasks/<phase>/<task>.md` for the
  spec contract — task specs are canonical.
- When a task is done, delete it from this file and add a one-line note
  to `CURRENT-STATE.md` in the "What's shipped" section.
- This file is a living punch list, not a project plan — reorganize
  freely.
