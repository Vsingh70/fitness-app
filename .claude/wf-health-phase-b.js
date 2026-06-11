export const meta = {
  name: 'health-phase-b',
  description: 'Build Google Health daily-metric sync (steps/sleep/HR/HRV) + pagination + reconnect handling',
  phases: [
    { title: 'Build' },
    { title: 'Review' },
    { title: 'Fix' },
  ],
}

const CTX = `
VGains FastAPI backend at /Users/vs/Desktop/Code/personal/fitness-app/apps/api (Python 3.12, uv, SQLAlchemy async, pydantic v2, ruff, mypy strict, pytest).
Extend the Google Health sync from weight-only to also pull STEPS, SLEEP, HEART RATE, and HRV into the daily_metric table.

CONFIRMED dataType IDs + JSON shapes (from a live probe 2026-06-07; times carry utcOffset like "-14400s" → bucket to the user's LOCAL day):
- steps (id "steps"): point.steps.interval.startTime (ISO UTC), point.steps.count is a STRING like "7". 1-minute buckets. DAILY steps = SUM of counts per local day.
- heart-rate (id "heart-rate"): point.heartRate.sampleTime.physicalTime (ISO UTC), point.heartRate.beatsPerMinute STRING "80". resting_hr ≈ MIN bpm per local day (no dedicated resting-HR type exists; resting-heart-rate returns 400).
- HRV (id "heart-rate-variability"): point.heartRateVariability.sampleTime.physicalTime, point.heartRateVariability.rootMeanSquareOfSuccessiveDifferencesMilliseconds is a NUMBER 75.1. hrv_ms = mean per local day.
- sleep (id "sleep"): ONE session per night. point.sleep.interval.startTime/endTime; point.sleep.summary.minutesAsleep STRING "250" → sleep_minutes directly. Sleep DAY = local date the session ENDS. There is NO sleep_score from the API → leave sleep_score null.

EXISTING CODE TO REUSE/MODIFY (read these first):
- apps/api/app/clients/google_health.py: has _list_data_points(access_token, data_type) doing a single bare GET to {API_BASE}/v4/users/me/dataTypes/{data_type}/dataPoints, returning body["dataPoints"] (list) or [] on 4xx, raising GoogleHealthAuthError on 401/403. ALSO has list_weight/list_body_fat (HealthMeasurement dataclass), _parse_time(sample_time)->datetime (parses sampleTime.physicalTime), Decimal import, RETRY_ATTEMPTS/RETRY_BACKOFF_SECONDS, GoogleHealthAuthError/GoogleHealthClientError. It ALSO currently contains a TEMPORARY probe block (ProbeResult dataclass, _PROBE_DATA_TYPES, _snippet, probe_data_types, and a logger.warning "PROBE_SHAPE" line + "import json") — REMOVE all of that probe code in this build.
- apps/api/app/services/health_sync.py: has sync_user(session, user_id) that refreshes token via _refresh_if_expiring, calls list_weight/list_body_fat, upserts body_metrics, sets connection.last_synced_at, returns HealthSyncResult(weight_written, body_fat_written). ALSO has a TEMPORARY probe_user() — REMOVE it. Reuses secretbox + google_health.refresh_tokens.
- apps/api/app/services/fitbit_sync.py: has _upsert_daily(session, user_id, summaries) using pg_insert(DailyMetric).on_conflict_do_update(index_elements=["user_id","date"], set_={...,"updated_at":_now()}). MIRROR this exactly for the new daily upsert.
- apps/api/app/models/daily_metric.py: DailyMetric(user_id, date (Date), steps:int|None, resting_hr:int|None, hrv_ms:Numeric(6,2)|None, sleep_minutes:int|None, sleep_score:int|None, readiness_score:int|None, created_at, updated_at). HAS a unique constraint uq_daily_metrics_user_date on (user_id, date) — so on_conflict works, NO migration needed.
- apps/api/app/routers/integrations_health.py: has the endpoints incl. a TEMPORARY POST /integrations/health/probe + imports of HealthProbeEntry/HealthProbeResponse — REMOVE the probe endpoint + those imports.
- apps/api/app/schemas/integrations_health.py: has HealthSyncResponse(weight_written, body_fat_written) + TEMPORARY HealthProbeEntry/HealthProbeResponse (+ "from typing import Any") — REMOVE the probe schemas (and the Any import if it becomes unused). EXTEND HealthSyncResponse with daily-metric counts (see deliverables).
- apps/api/app/workers/main.py: health_sync_all_periodic cron already calls health_sync.sync_user — no change needed unless the result tuple shape changes (it returns HealthSyncResult; the worker reads .weight_written + .body_fat_written — keep those fields, ADD new ones).
- apps/api/app/services/security/secretbox.py: encrypt/decrypt. apps/api/app/clients/google_health.py refresh_tokens(refresh_token=...) returns tokens w/ access_token, refresh_token, expires_at, scopes.

DELIVERABLES (modify in place; keep diffs tight + idiomatic; match surrounding style):

1) google_health.py:
   a) PAGINATION: change _list_data_points to follow body["nextPageToken"] across pages (append ?pageToken=... — verify the param name is plausible; Google uses pageToken). Cap at a safety MAX_PAGES (e.g. 25) and log a warning if the cap is hit (so silent truncation is visible). Keep the 401/403→GoogleHealthAuthError and 4xx→[] behavior; on a 4xx mid-pagination, stop and return what was collected.
   b) RECONNECT/INVALID_GRANT: in the token POST path (_post_token or refresh_tokens), detect HTTP 400 with body containing "invalid_grant" and raise GoogleHealthAuthError (NOT GoogleHealthClientError), so a dead 7-day Testing-mode refresh token is classified as auth failure rather than transient.
   c) NEW READERS returning typed daily aggregates. Add a frozen dataclass DailySummary(date: date, steps: int|None, resting_hr: int|None, hrv_ms: Decimal|None, sleep_minutes: int|None) and:
      - async def list_steps(access_token) -> list[DailySummary]  (sum counts per local day)
      - async def list_heart_rate(access_token) -> list[DailySummary]  (min bpm per local day -> resting_hr)
      - async def list_hrv(access_token) -> list[DailySummary]  (mean rmssd per local day -> hrv_ms)
      - async def list_sleep(access_token) -> list[DailySummary]  (minutesAsleep per session, keyed to local END date -> sleep_minutes)
      Use a shared helper to convert a point's physicalTime/interval.startTime + utcOffset string ("-14400s") into a LOCAL date. All numeric source values are STRINGS except rmssd (number) — parse defensively, skip unparseable points (never raise for one bad point).
      NOTE: these return PARTIAL DailySummary rows (each reader fills only its own field). The service merges them by date.
   d) REMOVE the entire probe block (ProbeResult, _PROBE_DATA_TYPES, _snippet, probe_data_types, the PROBE_SHAPE logger line, and the now-unused "import json" if json isn't used elsewhere).

2) health_sync.py:
   - REMOVE probe_user().
   - Add _merge_daily(summaries_lists) that merges the 4 readers' partial DailySummary lists into one dict[date]->merged DailySummary (combine non-null fields per date).
   - Add _upsert_daily_metrics(session, user_id, merged) mirroring fitbit_sync._upsert_daily (pg_insert(DailyMetric).on_conflict_do_update on ["user_id","date"], only SET fields that are non-null so one metric's sync doesn't wipe another's prior value — use COALESCE-style: in the on_conflict set_, only include a column when the new value is not None; simplest correct approach: build the set_ dict per row from non-null fields, always include updated_at). Return count of rows written.
   - Extend sync_user: after weight/body_fat, call the 4 readers, merge, upsert daily_metrics. Update HealthSyncResult to add daily_metrics_written: int. Keep weight_written/body_fat_written.
   - Wrap each reader call so one failing data type (e.g. raises) doesn't abort the whole sync — but let GoogleHealthAuthError propagate (so the cron/endpoint can mark reconnect). Log per-type failures.

3) schemas/integrations_health.py: REMOVE HealthProbeEntry/HealthProbeResponse (+ unused Any import). Add daily_metrics_written: int to HealthSyncResponse.

4) routers/integrations_health.py: REMOVE the probe endpoint + HealthProbeEntry/HealthProbeResponse imports. Update the /sync endpoint to return daily_metrics_written too.

5) workers/main.py: health_sync_all_periodic — update the line that totals results to include daily_metrics_written (it currently does result.weight_written + result.body_fat_written).

6) tests: update apps/api/tests/test_health_integration.py — the existing sync test monkeypatches google_health.list_weight/list_body_fat; ALSO monkeypatch the 4 new readers to return [] (or small fixtures) so the test still passes, and assert HealthSyncResponse now includes daily_metrics_written. Remove any probe-related test references if present.

CONSTRAINTS:
- Everything must pass: cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
- Do NOT run git. Do NOT touch the web app, infra, or unrelated files. Do NOT change DB models (the unique constraint already exists).
- Numeric source fields are STRINGS (except rmssd number) → parse with int()/Decimal() inside try/except; skip bad points.
- Preserve existing public behavior (weight sync, token refresh, last_synced_at).
`

phase('Build')
const buildResult = await agent(
  `${CTX}\n\nImplement ALL deliverables now. Read the listed existing files first to match idioms exactly, then make the edits with Edit/Write. After editing, RUN the verification suite yourself (cd apps/api && uv run ruff check . ; uv run ruff format . ; uv run mypy app ; uv run pytest -q) and FIX anything that fails before finishing. Report: files changed, the daily-aggregation logic you wrote, and the final verification output (ruff/mypy/pytest results).`,
  { label: 'build', phase: 'Build' },
)

phase('Review')
const REVIEW_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['file', 'severity', 'issue', 'fix'],
        properties: {
          file: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          issue: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
  },
}

const lenses = [
  'CORRECTNESS of the daily aggregation: verify steps SUM, heart-rate MIN→resting_hr, HRV MEAN, sleep minutesAsleep→sleep_minutes keyed to the LOCAL END date. Verify utcOffset-string ("-14400s") → local-date conversion is correct (parse the seconds offset, apply to the UTC physicalTime, take the date). Verify string vs number parsing per field and that bad points are skipped not crashed. Verify the merge across the 4 partial readers does not null-out a field another reader set, and the on_conflict_do_update does not overwrite an existing non-null column with null.',
  'PAGINATION + AUTH: verify _list_data_points actually follows nextPageToken (correct param name + termination + MAX_PAGES cap + a warning when capped), does not infinite-loop, and on a mid-pagination 4xx returns what it has. Verify 400 invalid_grant is raised as GoogleHealthAuthError and 401/403 still are. Verify a single failing data type in sync_user does not abort weight sync, but GoogleHealthAuthError still propagates.',
  'CLEANUP + COMPILE: verify ALL probe code is gone (ProbeResult, _PROBE_DATA_TYPES, _snippet, probe_data_types, PROBE_SHAPE log, probe endpoint, HealthProbeEntry/Response schemas, probe_user, the temporary "import json" if now unused, web/test refs). Verify no unused imports, mypy-clean types (Decimal/int|None), HealthSyncResponse + HealthSyncResult + the worker total all consistently include daily_metrics_written, and the test file monkeypatches the 4 new readers so pytest passes. Flag anything that would fail ruff/mypy/pytest.',
]

const reviews = await parallel(
  lenses.map((lens, i) => () =>
    agent(`${CTX}\n\nThe implementation is done. Adversarially review it — assume it has bugs and find concrete, real defects by READING the actual changed files. ${lens}\n\nOnly report substantiated defects (cite file + snippet). If correct, return empty findings.`,
      { label: `review#${i + 1}`, phase: 'Review', schema: REVIEW_SCHEMA })
  )
)

const findings = reviews.filter(Boolean).flatMap((r) => r.findings || [])
const blockers = findings.filter((f) => f.severity === 'blocker' || f.severity === 'major')

phase('Fix')
let fixResult = 'No blocker/major findings.'
if (blockers.length > 0) {
  fixResult = await agent(
    `${CTX}\n\nReviewers found these blocker/major defects. Fix EACH by editing the offending file (Read first). Then RE-RUN the full verification (cd apps/api && uv run ruff check . ; uv run ruff format . ; uv run mypy app ; uv run pytest -q) and report the final results. Do not run git.\n\nDEFECTS:\n${JSON.stringify(blockers, null, 2)}`,
    { label: 'fix', phase: 'Fix' },
  )
}

return { buildResult, totalFindings: findings.length, blockers: blockers.length, findings, fixResult }
