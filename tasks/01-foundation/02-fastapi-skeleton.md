# 01.02 FastAPI skeleton

## Context

The Python API is the only backend. Both Next.js and Swift talk to it. This task creates the skeleton so all later API tasks have something to build into.

Reference: `00-overview/api-conventions.md`.

## Goal

A running FastAPI service with database connection, structured logging, error handling, OpenAPI generation, and the `/v1/health` endpoint.

## Stack details

- Python 3.12
- FastAPI + Uvicorn (gunicorn in prod)
- SQLAlchemy 2.0 async + asyncpg
- Alembic for migrations
- Pydantic v2
- structlog
- python-jose for JWT
- ARQ for background jobs (configured, no jobs yet)
- uv for dependency management (or Poetry if uv proves rough)

## Layout

```
apps/api/
  app/
    main.py                  # FastAPI app factory
    config.py                # Pydantic Settings, loads from env
    db.py                    # async engine, session dependency
    deps.py                  # FastAPI dependencies (get_current_user, etc.)
    middleware/
      logging.py             # request id, structured logging
      errors.py              # exception handlers -> uniform error shape
    routers/
      __init__.py
      health.py
    models/                  # SQLAlchemy models
    schemas/                 # Pydantic request/response models
    services/                # business logic (kept thin in this task)
    workers/                 # ARQ task definitions
  alembic/
    env.py
    versions/
  tests/
    conftest.py
    test_health.py
  pyproject.toml
  Dockerfile
  .env.example
```

## Deliverables

1. FastAPI app with versioned router mounting (`/v1`).
2. `/v1/health` returns `{ "status": "ok", "version": "<git_sha>", "db": "ok" }`. The `db` field actually pings Postgres.
3. Structured JSON logging middleware. Every request logs `request_id`, `method`, `path`, `status`, `latency_ms`.
4. Uniform error response handler per `api-conventions.md`. Pydantic validation errors return the standard shape.
5. Alembic configured against the async engine, with a single initial migration that creates an `_alembic_version` row only (no app tables yet).
6. `pytest` configured, with a fixture that spins up a fresh database per test session using `pytest-postgresql` or a docker testcontainer.
7. Dockerfile (multi-stage: builder + runtime, runs as non-root).
8. `.env.example` documenting every required env var.

## Acceptance criteria

- `uv run uvicorn app.main:app --reload` starts cleanly against docker-compose Postgres.
- `curl localhost:8000/v1/health` returns 200 with the expected shape.
- `pytest` runs green with at least the health endpoint test.
- `alembic upgrade head` and `alembic downgrade base` both succeed against a clean db.
- `/openapi.json` is valid and contains the health endpoint.

## Dependencies

- `01.01 Monorepo setup`

## Out of scope

- Auth (next task).
- Any domain models (later tasks).
