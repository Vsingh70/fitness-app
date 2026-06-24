# Current state

Snapshot as of the last commit on `main` (149 commits in). Use this as the starting point when returning to the project after a break.

## What this is

A personal gym and nutrition app for the maintainer and a small group of training partners. Two clients (Next.js web, SwiftUI iOS) share a Python FastAPI backend with Postgres, Redis, and a self-hosted Ollama. The spec lives under `tasks/` (numbered phase files plus the redesign work packages under `tasks/redesign/`); the spec is canonical when it disagrees with code.

## At a glance

| | |
| --- | --- |
| Commits on `main` | 149 |
| Alembic migrations | 28 (`0001_baseline` through `0026_program_intensity_rep_mode`) |
| API routers | 17 (`apps/api/app/routers/*.py`) |
| ORM models | 21 (`apps/api/app/models/*.py`) |
| Backend tests | 417, under `uv run pytest` |
| Web tests | 52 cases, under `pnpm test` |
| OpenAPI spec | 13,829 lines (`packages/openapi/openapi.json`) |
| Clients | Next.js web (editorial design, most screens shipped); SwiftUI iOS (editorial visual port shipped, live data layer pending) |
| Deploy | Backend live on Hetzner; CD armed (a push to `main` auto-deploys the API) |

Repo: `https://github.com/Vsingh70/fitness-app`

## What's shipped

### Backend (phases 1-7, 9)
- Foundation: monorepo, FastAPI skeleton (structlog, lifespan, error envelopes), Apple and Google OIDC with JWT access plus rotating refresh, exercise library with pg_trgm search, CI workflows.
- Tracking: workout sessions API with nested exercises and sets, PR detection, soft delete and restore, idempotency keys.
- Programming: program templates plus custom programs, builder API, scheduling with tz-aware reminders.
- Progression: linear and double progression, RPE-based progression, mesocycles and deloads with a fatigue accumulator, Ollama-generated rationales with template fallbacks, and a block-vs-continuous periodization toggle.
- Analytics: per-muscle weekly volume rollups, strong/weak point analysis, per-exercise analytics.
- Nutrition: a self-hosted foods table bulk-ingested from USDA FoodData Central (Foundation, SR Legacy, Branded) and the Open Food Facts nightly dump, searched locally via pg_trgm (USDA generic ranked first, near-duplicate names de-duplicated) with a live Open Food Facts barcode fallback that caches; meals and meal items with daily totals, structured meal plans and meal-plan logging, body metrics. Ingest scripts under `apps/api/scripts/ingest/`; refresh runbook `docs/runbooks/food-data-refresh.md`. No paid food-data provider.
- Fitbit and health: Fitbit OAuth with encrypted tokens, sync worker, push-to-Fitbit, readiness score, plus a Google Health integration router added alongside Fitbit.
- Deployment: Ansible provisioning for the Hetzner VPS, B2-backed backups, CD pipeline (build, GHCR, SSH deploy, migrate gate, rollback), `/metrics` with the OpenTelemetry SDK, Grafana dashboards, alert rules, and runbooks.

### Editorial redesign (web + iOS)
- The editorial design system (warm paper and ink, clay accent, display serif, hairline surfaces) is implemented on both clients: web tokens in `apps/web/src/styles/tokens.css`, iOS in `apps/ios/GymApp/Core/Design/`. The canonical spec is `tasks/00-overview/design-system.md`.
- Web: every route ported to editorial (today, workouts, active session, summary, calendar, programs, exercises, nutrition, analytics, settings, sign-in).
- iOS: the SwiftUI app shell and feature views (Today, Workouts, Programs, Nutrition, Insights, Settings) are built against the editorial design system as a visual port.

### Feature redesigns on top of editorial
- Programs Direction A: first-run onboarding, an active-program spine with a mesocycle bar, a multi-program library (create, activate, delete), and a builder with a program-wide intensity mode (RPE, RIR, or off) and per-exercise range-vs-target reps. Shipped on web and iOS (migration `0026`). Spec: `tasks/redesign/claude-code-programs-A.md`, build manifest: `tasks/redesign/claude-code-programs-implementation.md`.
- Nutrition Direction A: a log-first day screen (calorie masthead plus a large quick-add search, no fixed meal slots), a P/C/F strip, and a flexible-vs-plan `nutrition_mode` chosen during first-run onboarding. Shipped on web; the iOS nutrition view is ported visually. Spec: `tasks/redesign/claude-code-nutrition-A.md`.

## What's not built or in flight

- iOS live data layer: the iOS app is a visual port with no networking yet. Wiring it to the API (the OpenAPI contract in `packages/openapi/openapi.json`) is the main iOS gap.
- FatSecret: removed. It was the planned food provider but never went live (no credentials, no IP allowlist) and its free tier was too shallow. Replaced by the self-hosted USDA + Open Food Facts ingest above (spec `tasks/redesign/07-nutrition.md`, migration `0029`). The first full Open Food Facts bulk import still needs to be run on the VPS off-hours.
- Google Health migration: the integration router exists; the full Fitbit-to-Google-Health cutover is in progress.
- Photo meal recognition: dropped, not built. It was specced (06.02) but cut in favor of manual entry, local food search, and barcode; the unused `meals.photo_url` column was removed. See `tasks/06-nutrition/02-photo-recognition.md`.
- Onboarding (phase 10): the interactive tour and public landing page are specced but not the current focus.

## Risks and known gaps

- OpenTelemetry sampling: a `ParentBased(TraceIdRatioBased(0.1))` sampler is wired; the "100 percent on errors" override still needs a custom sampler that inspects span status.
- JWT_SECRET rotation invalidates every access token because the app validates against one secret. Add `JWT_SECRET_PREVIOUS` support in `app/services/auth.py` to rotate seamlessly.
- Single-VPS rolling deploy recreates the container in place, so there is a brief restart gap; true zero downtime would need N+1 containers behind a proxy.

## Daily-use commands

```
# Backend
cd apps/api
uv run pytest -q
uv run ruff check . && uv run mypy app
uv run alembic upgrade head
uv run python -m scripts.export_openapi > ../../packages/openapi/openapi.json

# Frontend
cd apps/web
pnpm typecheck && pnpm test && pnpm lint
pnpm openapi:generate
pnpm dev

# CI and deploy
gh run list -L 10
gh workflow run api-deploy.yml --ref main
```

## Where to look first when picking this up

1. `tasks/README.md` for the phasing and `tasks/redesign/claude-code-*.md` for the redesign work packages
2. `tasks/00-overview/data-model.md` for the schema
3. `tasks/00-overview/api-conventions.md` for the response envelope shape
4. `tasks/00-overview/design-system.md` for the editorial design language
5. `apps/api/app/main.py` for the router wire-up
6. `docs/runbooks/` for deploy, rollback, restore, secrets, and incident response

## Path forward

In approximate priority:
1. Ship the remaining web page polish for the redesigned surfaces (programs, then nutrition).
2. Wire the iOS app's data layer to the API so the visual port becomes functional.
3. Provision FatSecret credentials and the IP allowlist to bring nutrition search live.
4. Add `JWT_SECRET_PREVIOUS` so secret rotation does not log everyone out.
