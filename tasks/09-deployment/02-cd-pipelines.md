# 09.02 Continuous deployment

## Context

CI verifies; CD ships. Web deploys via Vercel. API ships by building a container image and triggering the VPS to pull. iOS ships to TestFlight initially, App Store later.

## Goal

Push to main = automated deploy of web and API. iOS deploys manually-triggered from a workflow.

## Web (Vercel)

- Connect the `apps/web` directory as a Vercel project.
- Production branch: `main`. Preview deploys on every PR.
- Env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APPLE_SERVICE_ID`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, plus server-side `SESSION_SECRET`.
- Domain: `app.<domain>`.

## API

- GitHub Actions workflow on push to main:
  1. Build container image with the commit SHA tag.
  2. Push to GHCR (`ghcr.io/<org>/gym-api:<sha>`).
  3. SSH to the VPS, signal `app-deploy` systemd unit which `docker pull`s and rolls.
  4. Run `alembic upgrade head` inside the new container before swapping (use a sidecar `migrate` job that exits 0 before the new container starts serving).
- Tag `latest` after success.
- Slack/Discord webhook notification on success/failure.

## iOS

- `workflow_dispatch` in `.github/workflows/ios-release.yml`.
- Uses `fastlane`:
  - Bump build number.
  - Install certificates and provisioning profile via `match` (private repo).
  - Archive and export.
  - Upload to TestFlight.
  - Notify TestFlight testers.

## Rollback

- API: keep last 3 image tags. `app-rollback <sha>` Ansible task.
- Web: Vercel "Promote previous deployment".
- iOS: previous TestFlight build remains available for selection.

## Deliverables

1. Vercel project configured.
2. `.github/workflows/api-deploy.yml`.
3. `.github/workflows/ios-release.yml` with fastlane setup.
4. `app-deploy` and `app-rollback` Ansible tasks.
5. Slack/Discord webhook for deploy notifications.

## Acceptance criteria

- Push to main triggers a clean deploy of web in under 3 minutes.
- API deploy with a no-op migration completes in under 90 seconds with zero failed requests.
- Manually triggered iOS workflow lands a TestFlight build for internal testers.

## Dependencies

- `01.06 CI pipelines`
- `09.01 VPS provisioning`

## Out of scope

- Blue/green deploys on the API (single-server rolling is fine for this scale).
