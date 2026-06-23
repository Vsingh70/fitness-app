# 07.01 Fitbit OAuth and data import

## Context

Bidirectional Fitbit integration. This task: OAuth flow, token refresh, and pulling workouts + daily metrics + HR.

Reference: `00-overview/data-model.md` (fitbit_connections, fitbit_activities, daily_metrics).

## Goal

User connects Fitbit, we keep tokens fresh, and a worker syncs new data into our tables.

## OAuth

- Fitbit OAuth 2.0 with PKCE.
- Scopes: `activity`, `heartrate`, `sleep`, `weight`, `profile`.
- Redirect URIs: `https://app.<domain>/integrations/fitbit/callback` (web), and a custom scheme for iOS (`gymapp://integrations/fitbit/callback`).
- Tokens encrypted at rest using a libsodium secret-box, key from env (`FITBIT_TOKEN_KEY`).

## Endpoints

- `GET /v1/integrations/fitbit/authorize` returns the authorization URL + state token (CSRF). State stored signed in a short-lived JWT.
- `POST /v1/integrations/fitbit/callback` body `{ code, state, code_verifier }`. Exchanges for tokens, stores encrypted, upserts `fitbit_connections`.
- `DELETE /v1/integrations/fitbit` disconnects (revokes with Fitbit, deletes the row, keeps imported data).
- `GET /v1/integrations/fitbit/status` returns whether connected, last sync time, scopes.

## Sync worker

`apps/api/app/workers/fitbit_sync.py`:

- `sync_user(user_id)`:
  - Refresh token if expiring within 1 hour.
  - Pull activities from `/1/user/-/activities/list.json` since `last_synced_activity_at`.
  - Pull daily summaries (steps, RHR, sleep) for missing days back 14 days from today.
  - Upsert into `fitbit_activities` and `daily_metrics`.
- Scheduled every 30 minutes per connected user.
- Manual trigger: `POST /v1/integrations/fitbit/sync`.

## Rate limiting

Fitbit allows 150 requests/hour per user. Implement token-bucket per `fitbit_user_id` with conservative settings (avg 1/min). When throttled, requeue with backoff.

## Webhooks

Subscribe to Fitbit's webhook (subscriber API) so activities sync near-instantly for premium accounts. Implement:
- `POST /v1/webhooks/fitbit` receives notifications. Verify signature.
- On notification, enqueue `sync_user` for the affected user.

(If webhook subscription is not feasible during initial build, ship polling first and add webhooks later.)

## Deliverables

1. Migrations for `fitbit_connections`, `fitbit_activities`, `daily_metrics`.
2. Encryption helpers.
3. OAuth endpoints.
4. Sync worker + scheduler.
5. Webhook endpoint (or skeleton if subscribing is deferred).
6. Tests: token refresh, sync idempotency by `fitbit_log_id`, encryption roundtrip.

## Acceptance criteria

- Web OAuth round-trip completes and creates a `fitbit_connections` row.
- Triggering a manual sync inserts new activities and updates `daily_metrics`.
- Re-running sync inserts no duplicates.

## Dependencies

- `01.03 Auth`

## Out of scope

- Pushing our workouts to Fitbit (next task).
- Readiness scoring (later task).
