# CI

CI runs on every PR and push to `main`. Each app has its own workflow, gated by paths so a docs-only PR doesn't trigger app jobs. A nightly cron re-runs everything against `main` to catch flakes.

## Workflows

### [`api.yml`](../.github/workflows/api.yml)

Triggers: PRs and `main` pushes touching `apps/api/**`, `packages/openapi/openapi.json`, or the workflow itself.

Jobs:

- `lint`: `ruff check` + `ruff format --check`. Fails on style or rule violations.
- `typecheck`: `mypy app` in strict mode.
- `test`: spins up `postgres:16` and `redis:7` as services, runs `pytest -q`. Tests themselves use `testcontainers` to provision a per-session Postgres, but the service is there for parity with the local stack and as a fallback.
- `openapi`: runs `python -m scripts.export_openapi` and fails if the regenerated spec differs from `packages/openapi/openapi.json` in git. Forces the dev to commit the regenerated spec whenever the API surface changes.

### [`web.yml`](../.github/workflows/web.yml)

Triggers: PRs and `main` pushes touching `apps/web/**`, `packages/openapi/openapi.json`, or the workflow itself.

Jobs:

- `lint`: `pnpm lint` (Next.js + TS) + `pnpm format:check` (Prettier).
- `typecheck`: `tsc --noEmit`.
- `build`: `pnpm build` with mock env values so missing client IDs don't fail the build.
- `openapi-sync`: regenerates `apps/web/src/lib/api/types.ts` from the committed `packages/openapi/openapi.json` and fails on diff. Pairs with the API job's `openapi`: a schema change must be committed to both the spec and the generated TS types.

### [`ios.yml`](../.github/workflows/ios.yml)

Triggers: PRs and `main` pushes touching `apps/ios/**`, `packages/openapi/openapi.json`, or the workflow itself.

Currently a stub. Real Xcode build/test and Swift OpenAPI sync jobs land with task `08-ios/01`. The stub fails loudly if it detects an iOS project on disk while still being the stub, so we don't accidentally ship without proper CI.

### [`nightly.yml`](../.github/workflows/nightly.yml)

Triggers: cron at 06:00 UTC, plus manual `workflow_dispatch`.

Re-runs `api.yml`, `web.yml`, and `ios.yml` via `workflow_call`. If any leg fails, opens (or re-uses) a GitHub Issue labeled `ci-flake` so flakes don't get silently ignored.

## Branch protection

Configure once on the `main` branch in GitHub UI:

- Require status checks to pass before merging.
- Required checks:
  - `api / lint`
  - `api / typecheck`
  - `api / test`
  - `api / openapi`
  - `web / lint`
  - `web / typecheck`
  - `web / build`
  - `web / openapi-sync`
  - `ios / stub` (until task 08-ios/01 lands, then swap to `ios / build` and `ios / test`)
- Require branches to be up to date before merging.
- Do not allow administrators to bypass.

GitHub's "required checks" only fire when their workflow actually runs. The path filters above mean a README-only PR is auto-passed (none of the app workflows trigger). Pair branch protection with "auto-merge when all required checks pass" so trivial PRs don't get stuck.

## Debugging a red build

### `api / openapi` failed

You changed the API surface without regenerating the committed spec.

```
cd apps/api
uv run python -m scripts.export_openapi > ../../packages/openapi/openapi.json
git add ../../packages/openapi/openapi.json
git commit -m "chore: regenerate openapi spec"
```

This will also trigger `web / openapi-sync` because the spec changed, which probably fails until you regenerate the TS types too:

```
cd apps/web
pnpm openapi:generate
git add src/lib/api/types.ts
git commit -m "chore: regenerate web openapi types"
```

### `api / lint` failed on `ruff format --check`

```
cd apps/api && uv run ruff format .
```

### `api / typecheck` failed

mypy strict mode found a type problem. Fix at the source; do not add blanket `# type: ignore`.

### `api / test` failed

Pull the failing test's output. If it's a flake related to testcontainers ("could not pull image"), retry the workflow once; if it persists, file a `ci-flake` issue and investigate locally with `cd apps/api && uv run pytest <test_id>`.

### `web / lint` failed

```
cd apps/web && pnpm lint --fix && pnpm format
```

### `web / build` failed

Run `pnpm build` locally. The CI build uses mock env values (no real Google/Apple client IDs), so missing-env failures usually mean a server-side code path tried to read a required env at build time. Mark such reads as runtime-only.

### `nightly` opened a `ci-flake` issue

A scheduled run failed but normal PRs are passing. Likely flaky test or external dependency hiccup. The issue title contains the run id; follow the link to inspect.

## Local dry-run with `act`

`act` runs GH Actions workflows in local Docker containers. Useful for catching syntax errors and basic logic before pushing.

```
brew install act
# Validate workflow syntax
act -l
# Dry-run the API lint job
act pull_request -W .github/workflows/api.yml -j lint --container-architecture linux/amd64
```

`act` is not a perfect replica (it uses different base images, can't run macOS jobs at all, and has its own networking quirks), but it catches most syntax and step-ordering issues without a push.
