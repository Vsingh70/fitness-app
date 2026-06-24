# Project instructions

## Loop stop rules

The builder/checker team (`.claude/agents/builder.md`, `.claude/agents/checker.md`, driven by
`/loop`) loops until one of these is true:

- **All green:** every check in the task's definition of done passes. Stop and report success
  with the checker's final output as proof.
- **5 cycles used:** stop. Report what still fails and what was tried each cycle.
- **Same failure twice in a row:** stop. The builder is guessing, not fixing. Escalate to me.
- **A fix makes a previously passing check fail (regression):** stop. Something is being broken
  to fix something else. Escalate to me.

Never report success without checker output from the final cycle. Never weaken, delete, skip,
or loosen a test, type, or lint rule to reach all green — fix the code.

A task is "too large for the loop" if it cannot reach green inside 5 cycles. Break it into
smaller bounded tasks and loop each one. For the Programs flexible-model build, the bounded
tasks are the numbered tasks in
`docs/superpowers/plans/2026-06-22-programs-flexible-model.md`; run the loop one task at a time
in order, reviewing between tasks.

## Environment notes

- `apps/api` tests use testcontainers and **require Docker to be running**. Without it the
  checker cannot run the suite and the loop is unverified.
- API: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`. No static type
  checker is configured (ruff only).
- Web: `pnpm test`, `pnpm typecheck`, `pnpm lint`. OpenAPI types regenerate via
  `pnpm openapi:generate`; the contract is exported with `uv run python scripts/export_openapi.py`.
- Local Postgres occupies 5432, so the dockerized dev DB uses 5433.
