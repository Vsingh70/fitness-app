# Current state

Snapshot as of the last commit on `main`. Use this as the starting point when
returning to the project after a break.

## What this is

A personal gym + nutrition app built for the maintainer and a small group
of training partners. Spec lives under `tasks/` (33 numbered files across 9
phases); the spec is canonical when it disagrees with code.

## At a glance

| | |
| --- | --- |
| Commits on `main` | 32 |
| Alembic migrations | 17 (`0001_baseline` through `0016_fitbit_push`) |
| API routers | 17 (`apps/api/app/routers/*.py`) |
| API service modules | 43 |
| ORM models | 22 |
| Backend tests | 276, all passing under `uv run pytest` |
| Web tests | 30, all passing under `pnpm test` |
| OpenAPI spec | 10,235 lines (`packages/openapi/openapi.json`) |
| Workflows | api, api-deploy, web, ios, ios-release, nightly (all green on `main`) |
| Deferred | 5 iOS tasks (08.x), most of the web UI past skeleton |

Repo: `https://github.com/Vsingh70/fitness-app`

## What's shipped (28 of 33 tasks)

### Phase 1 — Foundation
- `01.01` monorepo + tooling
- `01.02` FastAPI skeleton (structlog, lifespan, error envelopes, middleware)
- `01.03` Apple + Google OIDC, JWT access + rotating refresh, dev `/v1/auth/dev`
- `01.04` exercise library with pg_trgm fuzzy search, owner-or-public scoping, custom CRUD
- `01.05` Next.js 15 skeleton with TanStack Query, Zustand, dnd-kit deps wired
- `01.06` CI workflows (api, web, ios stub, nightly)

### Phase 2 — Tracking
- `02.01` workout sessions API: sessions, exercises, sets, PR detection, soft delete + restore, idempotency keys
- `02.02 / 02.03` Web tracking + history UI **partially shipped** (skeleton pages exist at `apps/web/src/app/(app)/workouts/` and `(app)/`); component work past skeleton is deferred

### Phase 3 — Programming
- `03.01` program templates + custom programs (PPL, UL, Arnold, 5/3/1 seeds in `apps/api/seed/programs/`)
- `03.02` program builder pages (`apps/web/src/app/(app)/programs/`) — basic plumbing in place
- `03.03` scheduling: activation, recurrence, calendar page, hourly tz-aware workout reminders

### Phase 4 — Progression
- `04.01` linear + double progression with deload semantics + auto-applied recommendations
- `04.02` RPE-based progression with effective-RPE fallback, top-set averaging, e1RM cap, 3-strike deload
- `04.03` mesocycles + deloads + fatigue accumulator + `analytics_insights` stagnation surfacing
- `04.04` LLM rationale generation via Ollama with template fallbacks, ARQ-async writeback

### Phase 5 — Analytics
- `05.01` per-muscle weekly volume rollups with primary/secondary weighting, reactive + nightly recompute
- `05.02` strong/weak point analysis with strength norms, stagnation detection, imbalance + undertrained insights
- `05.03` per-exercise analytics endpoint (e1RM series, scatter, PRs, predicted next, variant suggestions)

### Phase 6 — Nutrition
- `06.01` foods table with OFF barcode lookup + USDA seed script, custom CRUD with archive
- `06.02` meal photo recognition via LLaVA with EXIF strip + signed URLs + rate limiting
- `06.03` meals + meal_items + meal_plans + body_metrics + Mifflin-St Jeor defaults

### Phase 7 — Fitbit
- `07.01` Fitbit OAuth with PKCE + libsodium-encrypted tokens at rest, sync worker, webhook handshake
- `07.02` push workouts to Fitbit with cardio detection + 409 dedup + opt-out toggle
- `07.03` readiness score (Mifflin-aware sleep/RHR/HRV formula) + low-readiness fatigue bump + reduce-today-volume endpoints

### Phase 9 — Deployment
- `09.01` Ansible playbook for Hetzner VPS (base hardening, Docker, Postgres, Redis, Ollama native, Caddy auto-TLS, monitoring); B2-backed nightly Postgres backups + photo sync; restore runbook
- `09.02` CD pipelines: api-deploy workflow (build → GHCR → SSH → systemd unit), `app-rollback` script with previous-image bookkeeping, migrate sidecar with `service_completed_successfully` gate, iOS skeleton Fastfile, Vercel config
- `09.03` `/metrics` endpoint with Bearer-gated Prometheus exposition, OpenTelemetry SDK (no-op until OTLP endpoint set), postgres + redis exporters, four Grafana dashboards, six alert rules, five new runbooks, BetterStack synthetic check template

## What's NOT built

### Deferred (Xcode required)
- `08.01` iOS skeleton (`tasks/08-ios/01-ios-skeleton.md`)
- `08.02` iOS tracking
- `08.03` iOS programming
- `08.04` iOS analytics
- `08.05` iOS nutrition

The CD pipeline for iOS exists (`.github/workflows/ios-release.yml` +
`apps/ios/fastlane/Fastfile`) and will run once 08.01 lands and the
six required secrets are configured in GitHub.

### Deferred under the established API-first pattern
Most "Web UI" deliverables from phases 2-7 ship a usable API + minimal
page skeleton but not the rich web frontend the task files describe.
The OpenAPI spec is committed at `packages/openapi/openapi.json` and
`pnpm openapi:generate` produces typed client code in
`apps/web/src/lib/api/types.ts`. Building out the UI is the main gap
between "shipped" and "useable by a non-developer in a browser." Tracked
holes (largest first):

- Workouts logging UI (set entry, exercise picker sheet, rest timer)
- Today screen with readiness tile + recommendation cards
- Nutrition logging (search, scan, photo tabs; daily totals ring)
- Insights cards with "Adjust program" deep-link
- Per-exercise analytics page (trends, sets, variants tabs)

### Awaiting external setup
These work, but need credentials / accounts the operator has to wire:

- Vercel project (settings live in `apps/web/vercel.json`)
- BetterStack synthetic monitor (template at `infra/synthetic/`)
- Grafana Cloud datasource + Discord webhook for alerts
- Backblaze B2 bucket + application key for backups
- GitHub Actions secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`,
  `DISCORD_WEBHOOK_URL`, plus the iOS bundle (see `apps/ios/README.md`)
- GitHub Actions variables: `APP_DOMAIN`, `DEPLOY_ENABLED=true` once the
  VPS is provisioned (currently absent, so the deploy job skips cleanly)

## Risks + known gaps

- **Six-commit OpenAPI drift bug**: between 5.03 and 7.03 the committed
  spec was generated by an inline `json.dumps` without `sort_keys=True`,
  but CI regenerates with the canonical script that DOES sort. Fixed at
  commit `8acf881`. Memory note in
  `~/.claude/projects/.../memory/feedback_openapi_regeneration.md`.
- **GHCR tag case**: GitHub usernames preserve case (`Vsingh70`) but OCI
  tags must be lowercase. Both `<sha>` and `:latest` tags now derive from
  a single bash `,,`-lowercased repo variable. Memory note in
  `feedback_docker_tag_case.md`.
- **OpenTelemetry "100% on errors"** is not yet implemented; current
  sampler is `ParentBased(TraceIdRatioBased(0.1))`. Adding the error
  override needs a custom sampler that inspects span status.
- **Ollama + Fitbit metric emission**: the Prometheus families
  (`OLLAMA_REQUESTS_TOTAL`, `FITBIT_SYNC_TOTAL`) are registered and the
  dashboards reference them, but the actual emit sites in
  `app/clients/ollama.py` and `app/services/fitbit_sync.py` weren't
  wired in 09.03. Five-line follow-up per module.
- **JWT_SECRET rotation** invalidates every access token because the app
  only validates against one secret. To rotate seamlessly, add
  `JWT_SECRET_PREVIOUS` support in `app/services/auth.py::verify_access_token`.
- **Single-VPS rolling deploy**: `app-deploy.sh` recreates the container
  in place (~2-5s gap during which the API restarts). The healthcheck
  blocks traffic resumption until the new container is ready. True zero
  downtime would need nginx-style upstream pooling with N+1 containers.

## Daily-use commands

```
# Backend
cd apps/api
uv run pytest -q                              # 276 tests
uv run ruff check . && uv run mypy app
uv run alembic upgrade head
uv run python -m scripts.export_openapi > ../../packages/openapi/openapi.json

# Frontend
cd apps/web
pnpm typecheck && pnpm test && pnpm lint
pnpm openapi:generate                         # regenerate types.ts
pnpm dev                                      # http://localhost:3000

# CI status
gh run list -L 10
gh run watch <run-id> --exit-status

# Deploy (once VPS is up)
gh workflow run api-deploy.yml --ref main
ssh ops@<host> sudo /usr/local/bin/gymapp-app-deploy
ssh ops@<host> sudo /usr/local/bin/gymapp-app-rollback previous
```

## Where to look first when picking this up

1. `tasks/README.md` for the phasing
2. `tasks/00-overview/data-model.md` for the schema
3. `tasks/00-overview/api-conventions.md` for the response envelope shape
4. `apps/api/app/main.py` for the router wire-up (17 routers in one place)
5. `docs/runbooks/` for incident response, deploy, rollback, restore, secrets,
   ollama, fitbit, and migration-failure procedures
6. This file when you forget what's where

## Path forward

In approximate priority:

1. Stand up the Hetzner VPS and run the Ansible playbook (09.01 was
   written but never executed against real infrastructure). Once the
   four `DEPLOY_*` GitHub secrets are set, flip `DEPLOY_ENABLED=true`
   and the next push deploys for real.
2. Build the web UI for workouts logging — it's the most-used path and
   the largest gap between "API works" and "I can use this in my browser."
3. When a Mac with Xcode 16 is available, run 08.01 to generate the iOS
   skeleton; subsequent 08.x tasks fill in features per phase.
4. Wire the deferred Ollama + Fitbit metric emit sites (one afternoon).
5. Add `JWT_SECRET_PREVIOUS` support so secret rotation doesn't log
   everyone out (one afternoon).
