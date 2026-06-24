# 01.01 Monorepo setup

## Context

Web (Next.js), iOS (Swift), and Python API will all live in the same repo. Single source of truth for the OpenAPI spec, shared docs, and CI configuration.

## Goal

Create the repo skeleton and shared tooling. No application code yet, just the structure other tasks will build into.

## Layout

```
gym-app/
  apps/
    api/                  # FastAPI service
    web/                  # Next.js 15 app
    ios/                  # Swift package + Xcode project
  packages/
    openapi/              # Generated OpenAPI spec lives here after API build
  scripts/                # Dev scripts (db reset, seed, etc.)
  docs/                   # Architecture docs, runbooks
  .github/workflows/      # CI
  docker-compose.yml      # Local dev: postgres, redis, ollama
  .editorconfig
  .gitignore
  README.md
```

## Deliverables

1. Init git repo with above structure (empty app folders are fine for now).
2. Root `README.md` describing the structure and how to run each app.
3. `docker-compose.yml` with services:
   - `postgres:16` on port 5432
   - `redis:7` on port 6379
   - `ollama/ollama` on port 11434 with a named volume for model storage
4. `.editorconfig` enforcing LF line endings, 2-space indent for TS/JSON/YAML, 4-space for Python, tabs for Swift.
5. Root `.gitignore` covering Python, Node, Swift, macOS, env files.
6. `scripts/dev-up.sh` that boots docker-compose and prints next steps.
7. `scripts/dev-down.sh`.

## Acceptance criteria

- `docker compose up` boots all three services healthy.
- Root README documents how to start everything from a clean clone in under 5 commands.
- No secrets committed. `.env.example` files in each app folder (will be filled in by later tasks).

## Dependencies

None. This is task zero.

## Out of scope

- Any application code.
- CI (separate task).
