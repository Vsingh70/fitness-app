# Gym app

Monorepo for a training operating system. Web (Next.js), iOS (Swift), and a Python FastAPI backend share one repo and one OpenAPI spec.

The project overview, phasing, and full task index live in [tasks/README.md](tasks/README.md). Schema, API rules, and the design system live in [tasks/00-overview/](tasks/00-overview/). Treat those as authoritative.

## Layout

```
apps/
  api/          FastAPI service (Python 3.12)
  web/          Next.js 15 app (TypeScript)
  ios/          Swift 6 / SwiftUI app
packages/
  openapi/      Generated OpenAPI spec (produced by the API build)
scripts/        Dev helpers (dev-up, dev-down, etc.)
docs/           Architecture notes and runbooks
tasks/          Numbered build plan, one folder per phase
.github/workflows/   CI
docker-compose.yml   Local services: postgres, redis, ollama
```

The `apps/` folders are scaffolded empty here. Later tasks under `tasks/01-foundation/` fill them in.

## Local services

`docker-compose.yml` runs the three services every app needs locally:

- `postgres:16` on `localhost:5432` (user `gym`, password `gym`, db `gym`)
- `redis:7` on `localhost:6379`
- `ollama/ollama` on `localhost:11434`, with a named volume so pulled models survive restarts

## Bootstrap from a clean clone

```
git clone <repo> gym-app
cd gym-app
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
scripts/dev-up.sh
```

`dev-up.sh` boots the docker stack with health checks and prints the next steps for each app. `scripts/dev-down.sh` stops everything (volumes preserved).

## Per-app commands

These wire up in later foundation tasks. Listed here so the bootstrap story is visible end to end.

- API: `cd apps/api && uv sync && uv run uvicorn app.main:app --reload`
- Web: `cd apps/web && pnpm install && pnpm dev`
- iOS: open `apps/ios` in Xcode

## Conventions

- No em dashes or en dashes anywhere (code, prose, UI copy).
- Python: ruff + black, type hints, Pydantic v2.
- TypeScript: strict mode, no `any`, Zod at API boundaries.
- Swift: SwiftUI first, async/await.
- Commits: conventional commits, one logical change per commit, reference the task file in the body.
