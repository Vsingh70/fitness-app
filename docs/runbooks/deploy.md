# Deploy runbook

Day-to-day deploys are automated. This doc covers what runs, how to trigger
manually, and how to roll back. There are three deploy targets:

| Target | Triggered by | Path |
| ------ | ------------ | ---- |
| Web    | Vercel (push to main) | Vercel project linked to `apps/web/` |
| API    | GitHub Actions (push to main) | `.github/workflows/api-deploy.yml` |
| iOS    | GitHub Actions (manual `workflow_dispatch`) | `.github/workflows/ios-release.yml` |

## API: automatic deploy

A push to `main` that touches `apps/api/**` or `infra/**` runs:

1. `api.yml` (CI): lint, typecheck, pytest, openapi drift check. Must succeed
   before the deploy starts.
2. `api-deploy.yml`:
   - Builds the API container with `GIT_SHA={first-12-of-commit}`.
   - Pushes to `ghcr.io/<org>/<repo>-api:<sha>` AND tags `:latest`.
   - SSH'es to the VPS and runs `sudo systemctl start gymapp-app-deploy.service`.
   - Posts a Discord notification to `DISCORD_WEBHOOK_URL` (skipped if the
     secret isn't configured).

The VPS-side `gymapp-app-deploy` systemd unit invokes
`/usr/local/bin/gymapp-app-deploy`, which:

1. Snapshots the currently-running image's digest into
   `/etc/gymapp/previous-image` for one-command rollback.
2. `docker compose pull` for `migrate`, `api`, `worker`.
3. `docker compose run --rm migrate` — runs `alembic upgrade head` to
   completion. If it exits non-zero the deploy aborts before the api swaps,
   so the old api keeps serving against the old schema.
4. `docker compose up -d --no-deps api` — recreates the api container.
5. Polls `http://127.0.0.1:8000/v1/health/ready` for up to 90s. Aborts and
   dumps `docker compose logs` if the new container never becomes healthy.
6. `docker compose up -d --no-deps worker` — rolls the ARQ worker.

The deploy script writes the previous-image bookkeeping **before** pulling,
so a failed deploy leaves the file pointing at the still-running image.
That's what `gymapp-app-rollback previous` reads.

## API: required GitHub secrets

| Secret | Purpose |
| ------ | ------- |
| `DEPLOY_HOST` | VPS hostname or IP (e.g. `api.example.com`) |
| `DEPLOY_USER` | SSH user, usually `ops` |
| `DEPLOY_SSH_KEY` | Private key authorized for `ops@DEPLOY_HOST` |
| `DISCORD_WEBHOOK_URL` | Discord webhook (optional; notify step skipped if unset) |

Also required as a repo variable:

| Variable | Purpose |
| -------- | ------- |
| `APP_DOMAIN` | Used in the deploy environment URL (e.g. `api.example.com`) |

## API: manual deploy

Two options, both from your laptop:

**Re-run the latest workflow** (cleanest):

```
gh workflow run api-deploy.yml --ref main
```

**Skip CI, deploy whatever's at `:latest`** (use sparingly):

```
ssh ops@<host> sudo systemctl start gymapp-app-deploy.service
```

Both run the same VPS script and produce the same outcome.

## API: rollback

One-command rollback to the previous image:

```
ssh ops@<host> sudo /usr/local/bin/gymapp-app-rollback previous
```

Rollback to a specific SHA:

```
ssh ops@<host> sudo /usr/local/bin/gymapp-app-rollback <12-char-sha>
```

The rollback script:

1. Resolves the target image (from `/etc/gymapp/previous-image` or the SHA arg).
2. `docker pull`s it.
3. Re-tags it as `:latest` so the compose file picks it up.
4. Re-runs `alembic upgrade head` (idempotent — no-op if you're rolling to a
   schema-equivalent image).
5. Brings up the api container, polls health, then rolls the worker.

If the rollback fails mid-flight, the deploy script's snapshot at
`/etc/gymapp/previous-image` still points at the original "previous"
image, so `gymapp-app-rollback previous` is repeatable.

**Schema rollbacks are intentionally not automated.** If the bug you're
rolling away from is a migration, downgrade Alembic manually:

```
sudo docker compose -f /etc/gymapp/app-compose.yml run --rm migrate \
  alembic downgrade -1
```

Or use the [restore runbook](restore.md) to load a pre-migration backup.

## Web: automatic deploy

Vercel watches `main` and deploys `apps/web/` on every push. Previews go up
for every PR. Configuration lives at:

- `apps/web/vercel.json` — build command, security headers, region pin
- Vercel project settings → Environment Variables — the actual values

See `apps/web/.vercel-env.example` for the required variables.

## Web: rollback

Vercel dashboard → Deployments → previous successful build → "Promote to
Production." Takes ~30 seconds.

## iOS: manual deploy

Currently a skeleton — the Xcode project from `tasks/08-ios/01-ios-skeleton.md`
isn't shipped yet. The workflow file is in place so we can wire it up when
the project lands.

To trigger once it works:

```
gh workflow run ios-release.yml --field lane=beta
```

See `apps/ios/README.md` for the secret matrix and one-time match setup.

## iOS: rollback

TestFlight keeps previous builds available. In App Store Connect →
TestFlight, pick the previous build and re-distribute it to the same
group. No CI involvement needed.

## Smoke test after any API deploy

```
curl -fs https://api.<domain>/v1/health/ready
curl -fs https://api.<domain>/v1/health/live
ssh ops@<host> sudo docker logs --tail=50 gymapp-api
ssh ops@<host> sudo docker logs --tail=50 gymapp-worker
```

If any of those fail, roll back immediately with
`gymapp-app-rollback previous`.

## Database migrations

The `migrate` sidecar in `app-compose.yml` runs `alembic upgrade head` to
completion before the api container starts. Long or destructive migrations
(adding NOT NULL to a non-empty column, dropping tables, etc.) should be
deployed in two PRs:

1. PR 1: ship the additive migration + code that tolerates both shapes.
2. PR 2 (after observing PR 1 in prod for >24h): drop the old shape.

Coordinate destructive migrations with the user before merging.

## Past incidents

Document them inline here. None yet.
