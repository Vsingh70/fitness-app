# Fitbit → Google Health migration — status & runbook

**Why:** Fitbit discontinued new legacy-app registration; the legacy Web API
sunsets **September 2026**. The original Fitbit integration targeted that legacy
API, so "Connect Fitbit" failed (no obtainable `client_id`). The supported path
is the **Google Health API** (Fitbit data, rebuilt on Google infra, standard
Google OAuth 2.0). This doc is the live status of that migration.

**Status as of 2026-06-10: SHIPPED, migration closed out.** Weight, body-fat,
steps, sleep, resting HR, and HRV all sync from a connected Fitbit account into
the app and are surfaced in the UI, live in production. The **legacy direct-Fitbit
integration has been fully removed** (Phase 4 cleanup) and **ECG was abandoned and
reverted** — the probe confirmed ECG data is technically available, but the Google
Health API's polling cadence (≥30-min cron; no real-time path) can't refresh a
waveform fast enough to be clinically/UX useful, so the spike was torn out
(scope + probe removed). The only remaining item is the deferred OAuth
verification. Details below.

---

## How it works now (current implementation)

**Auth.** Google OAuth 2.0 + PKCE via a dedicated OAuth client in the existing
sign-in Google Cloud project. Tokens are stored encrypted (secretbox) in the
`fitbit_connections` table (kept provider-agnostic; not renamed). The OAuth app
is in **Testing** mode → refresh tokens expire after ~7 days (see "Reconnect"
below). Scopes requested (`app/clients/google_health.py` `DEFAULT_SCOPES`):
`googlehealth.health_metrics_and_measurements.readonly`,
`...activity_and_fitness.readonly`, `...sleep.readonly`, plus `openid`.
(`...ecg.readonly` was added for the ECG probe, then removed when ECG was
abandoned — see below.)

**Data flow.** `watch → Fitbit phone app (Bluetooth) → Google Health cloud →
VGains reads`. VGains only controls the last hop, so true real-time is
impossible; realistic freshness is ~30 min after the watch reaches the cloud.

**Read API.** `GET https://health.googleapis.com/v4/users/me/dataTypes/{id}/dataPoints`
(bearer token). dataPoints are **newest-first**, paginated via `nextPageToken`.
No working server-side time filter (`?filter=` and `:dailyRollUp` both 400) — so
the client paginates with **client-side early-stop** keyed on `since` (capped at
`MAX_PAGES=25`). Confirmed dataType IDs + payload shapes are documented in the
`reference_google_health_*` memory files; key ones:
- `weight` → `weight.weightGrams/1000`, `weight.sampleTime.physicalTime`
- `body-fat` (hyphen) → body-fat percentage
- `steps` → sum of `steps.count` (1-min buckets) per local day
- `heart-rate` → `heartRate.beatsPerMinute`; resting HR = daily MIN
- `heart-rate-variability` → `...rootMeanSquareOfSuccessiveDifferencesMilliseconds`; daily mean
- `sleep` → `sleep.summary.minutesAsleep`, keyed to the local date the session ENDS
- (NO `resting-heart-rate`, `sleep-score`, `spo2` IDs — those 400; derive/skip.)

**Sync triggers.** (1) Manual "Sync now" button in Settings → `POST
/integrations/health/sync`. (2) ARQ cron `health_sync_all_periodic` every 30 min
(:15/:45), syncing all connected users. Reads are **incremental**:
`compute_since(last_synced_at)` = `now-30d` on first sync (bounded backfill) else
`last_synced_at - 2d` (overlap for late/edited data). Upserts are idempotent
(`body_metrics` de-duped by recorded_at; `daily_metrics` on `(user_id, date)`,
writing only non-null fields so one metric never wipes another's value).

**Reconnect handling.** A dead 7-day refresh token returns `400 invalid_grant`,
now classified as `GoogleHealthAuthError` (not a transient error). On that error
the connection's `needs_reauth` flag is set; `/sync` returns 409; the status
endpoint exposes `needs_reauth`; the web shows an app-level "Reconnect Fitbit"
banner + a Settings reconnect button. Cleared on the next successful sync or
reconnect.

**Surfaces.** `/body` page (weight history + trend + manual log); `/health` page
(steps/sleep/resting-HR/HRV stat tiles + 30-day trend charts); Today dashboard
tiles (weight, steps, sleep) + the readiness tile (fed by sleep/HR/HRV).

---

## What's been implemented (✅ DONE, in production)

- **Phase 0 — Register.** Health API enabled; OAuth client + scopes + test users
  configured in the sign-in GCloud project; creds in vault
  (`vault_google_health_client_id/secret`); redirect URI points at the **Vercel**
  origin `…/integrations/health/callback` (NOT the API domain — a 404 trap that
  was hit and fixed).
- **Phase 1 — Client + OAuth.** `app/clients/google_health.py` (token
  exchange/refresh, PKCE authorize URL, data reads w/ pagination + early-stop),
  `app/services/health_oauth.py` (authorize/callback/disconnect),
  `app/routers/integrations_health.py`, `app/schemas/integrations_health.py`.
  Endpoint discovery was done via temporary self-probes (now removed).
- **Phase 2 — Sync + weight + daily metrics.** `app/services/health_sync.py`:
  weight/body-fat → `body_metrics`; steps/sleep/resting-HR/HRV → `daily_metrics`
  (local-day bucketed). Daily ARQ cron `health_sync_all_periodic` (:15/:45).
  Incremental early-stop reads (commit `d6ec5d3`). End-to-end verified live
  (232+ days backfilled on first real sync, no errors).
- **Phase 3 — Web.** `/body` + `/health` pages, Today tiles, readiness tile fed,
  Settings "Fitbit (via Google)" card (Connect/Sync now/Disconnect), reconnect
  banner.
- **Reliability — reconnect prompt.** `needs_reauth` column (migration `0018`),
  set/clear wiring, 409 on `/sync`, app-level banner (commit `46e1843`).
- **Phase 4 — legacy Fitbit removal (DONE).** The old direct-Fitbit Web API
  integration is fully deleted on both surfaces. Backend: removed `clients/fitbit.py`,
  `services/fitbit_oauth.py` + `_enqueue`, `fitbit_sync.py`, `fitbit_push.py` +
  `_enqueue`, `routers/integrations_fitbit.py`, `schemas/integrations_fitbit.py`,
  `models/fitbit_activity.py`; removed the `fitbit_sync_all_periodic` (:00/:30) cron
  + its worker tasks, the `push-to-fitbit`/`fitbit-link` workout endpoints, the
  `auto_push_to_fitbit` user preference, the `FITBIT_SYNC_TOTAL` metric, and the
  legacy `fitbit_client_id/secret/redirect_uri/webhook_*` config. Migration
  `0019_drop_legacy_fitbit` drops the `fitbit_activities` table + the
  `users.auto_push_to_fitbit` / `workout_sessions.fitbit_log_id` /
  `workout_sessions.fitbit_pushed_at` columns (round-trip verified). Web: deleted
  `lib/api/fitbit.ts`, `lib/hooks/fitbit.ts`, the legacy `integrations/fitbit/callback`
  page, and the legacy Fitbit settings card; `generatePkce` extracted to the shared
  `lib/utils/pkce.ts` (Google Health still uses it). OpenAPI + web types regenerated.
  **KEPT (shared with Google Health):** the `fitbit_connections` table + `FitbitConnection`
  model, `Settings.fitbit_token_key` (encrypts the Google Health tokens via `secretbox`),
  and the `health_sync_all_periodic` (:15/:45) cron.
- Key commits: `aaf40fb` (weight), `8a941af` (daily metrics), `75fc1fd`
  (/health + tiles), `d6ec5d3` (incremental reads), `46e1843` (reconnect),
  `b9ac416` (ECG scope + probe spike), `fed6473` (Phase 4 legacy-Fitbit removal).
  The ECG revert (scope + probe teardown) lands in a follow-up commit on the
  `chore/remove-legacy-fitbit` branch.

---

## What's left to work on (⬜ TODO)

- **✅ Phase 4 cleanup — legacy Fitbit removal — DONE.** Completed 2026-06-10; see
  the "What's been implemented" section above for the full inventory. The noisy
  `fitbit_sync_all_periodic` (:00/:30) cron, all legacy client/oauth/sync/push code,
  the web fitbit api/hooks/callback, and the `FITBIT_*` OAuth/webhook config are gone;
  migration `0019_drop_legacy_fitbit` drops the dead tables/columns. (Staged in the
  working tree, not yet committed.)
- **✅ ECG — ABANDONED & REVERTED — DONE.** The probe (`b9ac416`) confirmed ECG data
  *is* exposed to third-party apps with waveform samples, but ECG was dropped anyway:
  the Google Health read model is poll-only (≥30-min cron, no real-time / push that
  arrives fast enough), so a waveform would always be too stale to be useful. The whole
  spike was torn out — the `googlehealth.ecg.readonly` scope removed from `DEFAULT_SCOPES`,
  and the probe endpoint / `probe_ecg_*` / `ProbeResult` / `HealthProbe*` schemas / web
  `probeEcg`/`useProbeEcg` + "Discover ECG" button / `PROBE_SHAPE` logging all deleted.
  No DB migration needed (the granted-scopes column just stops getting the ecg string on
  future re-consents; existing rows are harmless). OpenAPI + web types regenerated.
- **⬜ OAuth verification (DEFERRED, optional).** Publishing the app to remove the
  7-day token expiry requires full Google verification for restricted health
  scopes: privacy policy + homepage on an owned domain, domain verification, a
  consent-flow demo video, and likely a paid **CASA security assessment** (~weeks).
  Decided NOT worth it for friends-and-family; **stay in Testing mode** and let
  the reconnect banner handle the ~weekly re-auth. Revisit only if opening the
  app beyond friends.

---

## Decisions (RESOLVED)

1. **Label:** user-facing **"Fitbit (via Google)"**; backend table names unchanged.
2. **Push-to-Fitbit:** **DROPPED** — read-only ingest only (`fitbit_push.py` and the
   `auto_push_to_fitbit` preference removed in Phase 4).
3. **Webhooks:** **NOT used.** Google Health subscriptions exist but still require
   an authenticated read after the ping + a stable public endpoint; not worth it
   for <100 users. The 30-min cron + on-demand "Sync now" is the model. (Possible
   future: sync-on-app-open for instant freshness.)
4. **GCloud project:** reused the existing sign-in project.
5. **Publish/verify:** DEFERRED (stay in Testing + reconnect banner) — see above.

## Known limitations / notes

- **Freshness** is bounded by the watch→phone Bluetooth hop (minutes–hours) +
  the 30-min cron; never "real-time". "Sync now" only collapses the last hop.
- **High-frequency coverage** (steps/HR) fills in FORWARD over days via incremental
  reads; a single backfill can't deeply cover minute-level metrics within
  `MAX_PAGES`. Sleep/HRV (low-frequency) backfill deeply immediately.
- **No `sleep_score`** from the API (Google doesn't expose Fitbit's score) — left null.
- Shapes/IDs live in memory files `reference_google_health_api` +
  `reference_google_health_daily_shapes`.
