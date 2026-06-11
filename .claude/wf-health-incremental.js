export const meta = {
  name: 'health-incremental-reads',
  description: 'Incremental early-stop reads so steps/HR coverage fills in (keyed on last_synced_at)',
  phases: [{ title: 'Build' }, { title: 'Review' }, { title: 'Fix' }],
}

const CTX = `
VGains FastAPI backend at /Users/vs/Desktop/Code/personal/fitness-app/apps/api (Python 3.12, uv, SQLAlchemy async, ruff, mypy strict, pytest).

PROBLEM: The Google Health daily-metric sync (steps/sleep/HR/HRV → daily_metrics) works, but coverage is LOPSIDED. After the first real sync: sleep 228 days, hrv 18, steps 6, resting_hr 1. Cause: dataPoints come NEWEST-FIRST and the reader paginates from page 1 with a hard MAX_PAGES=25 cap. High-frequency metrics (steps + heart-rate are minute-level, ~1440 points/day) blow through 25 pages while still in recent days, AND each sync re-reads the same recent history from scratch (last_synced_at is set but never used to bound reads). Sleep (1/night) + HRV (sparse) paginate cleanly so they look fine.

CONFIRMED FACTS:
- dataPoints are returned NEWEST-FIRST (the probe's first heart-rate point was today's most-recent reading).
- There is NO working server-side time filter: ?filter= and :dailyRollUp both return 400 (from the spike). Only pageToken works. So the fix is CLIENT-SIDE early-stop pagination.
- last_synced_at is a column on fitbit_connections, currently set after each sync but NOT used to bound reads.

CURRENT CODE (apps/api/app/clients/google_health.py):
- _get_data_points_page(access_token, data_type, page_token) -> (points, nextPageToken). 401/403 -> GoogleHealthAuthError; other 4xx -> ([],None); newest-first.
- _list_data_points(access_token, data_type) -> list[dict]: loops _get_data_points_page following nextPageToken, capped at MAX_PAGES=25, warns if capped.
- Readers list_steps/list_heart_rate/list_hrv/list_sleep each call _list_data_points then aggregate per LOCAL day via _local_date(iso, offset) (parses physicalTime/interval times + utcOffset string). Each returns list[DailySummary(date, steps?, resting_hr?, hrv_ms?, sleep_minutes?)]. Helpers: _to_int, _parse_offset_seconds, _local_date, _parse_time. list_weight/list_body_fat also use _list_data_points (weight/body-fat are low-frequency; leave their behavior unchanged — but they can accept the same since param defaulting to None = no bound).
- The per-point timestamp to compare against 'since': steps uses point.steps.interval.startTime; sleep uses point.sleep.interval.endTime; heart-rate uses point.heartRate.sampleTime.physicalTime; hrv uses point.heartRateVariability.sampleTime.physicalTime; weight uses point.weight.sampleTime.physicalTime; body-fat similar. (These are the SAME fields the readers already extract for bucketing.)

CURRENT CODE (apps/api/app/services/health_sync.py):
- sync_user(session, user_id): refreshes token, calls list_weight/list_body_fat + the 4 daily readers via _safe_read(name, reader, access_token=...), merges, upserts daily_metrics, sets connection.last_synced_at = _now(). HealthSyncResult(weight_written, body_fat_written, daily_metrics_written).
- _safe_read isolates per-type failures (returns []), lets GoogleHealthAuthError propagate.

DELIVERABLES (modify in place, tight idiomatic diffs, no behavior regressions for weight):

1) google_health.py — EARLY-STOP PAGINATION + per-reader 'since':
   a) Add an optional 'since: datetime | None = None' param to _list_data_points. While paginating newest-first, after each page, if 'since' is set and EVERY point on the page is older than 'since' (by the point's own timestamp — see (c)), STOP (we've paged past the new window). To know each point's time generically, accept an optional 'point_time: Callable[[dict], datetime | None] = None'; if provided, use it to extract a point's timestamp and stop once the newest-remaining points are all < since. Simplest robust rule: track whether ANY point on the page is >= since; once a full page has NO point >= since, stop (since order is newest-first, all further pages are older). If point_time is None, behavior is unchanged (full pagination to MAX_PAGES).
   b) Keep MAX_PAGES=25 as the hard safety cap, but raise it to a higher per-call ceiling ONLY if needed for backfill — instead, since early-stop now bounds steady-state reads, ADD a separate larger cap for the first/backfill sync is NOT needed; keep MAX_PAGES=25. Document that with early-stop, 25 pages comfortably covers an incremental window.
   c) Each reader passes a 'point_time' extractor matching its timestamp field, and threads 'since' down. Add 'since: datetime | None = None' to list_steps/list_heart_rate/list_hrv/list_sleep (and list_weight/list_body_fat for consistency, default None). A point with an unparseable time should NOT trigger early-stop (treat as "keep going" / >= since) to avoid dropping data on a malformed point.
   d) Add module constants: BACKFILL_DAYS = 30 (first-sync window for high-frequency metrics) and OVERLAP = timedelta(days=2) (re-read recent days to catch late-arriving/edited data). Export a helper compute_since(last_synced_at: datetime | None) -> datetime that returns now-BACKFILL_DAYS on first sync (last_synced_at None) else last_synced_at - OVERLAP. (Service can also compute this; put the constants + helper in the client so they're testable.)

2) health_sync.py — USE last_synced_at to bound reads:
   - In sync_user, compute 'since = google_health.compute_since(connection.last_synced_at)' BEFORE refreshing/reading, and pass since=since to all 6 readers (weight/body_fat too — harmless, bounds their reads similarly).
   - IMPORTANT ordering bug to avoid: read last_synced_at into 'since' BEFORE you overwrite connection.last_synced_at = _now() at the end. (It already sets it at the end, so just capture since at the start.)
   - _safe_read must forward the since kwarg to the reader.
   - Keep upsert_daily_metrics writing only non-null fields (so a metric absent from this window's pages doesn't wipe a prior value).

3) Tests (apps/api/tests/test_health_integration.py): the existing sync test monkeypatches the readers; ensure they still accept the new since kwarg (monkeypatched fakes should accept **kwargs or since=None). Add/adjust a test that:
   - first sync (last_synced_at None) computes since ~= now - 30d;
   - a reader with since stops early when a page is all-older (unit-test _list_data_points early-stop with a fake _get_data_points_page returning 2 pages where page 2 is all older than since → assert page 3 is never requested). Mock at the _get_data_points_page level.
   Keep all existing assertions passing.

CONSTRAINTS:
- Must pass: cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
- Do NOT change DB models or add migrations (last_synced_at already exists). Do NOT touch web/infra. Do NOT run git.
- Preserve: weight/body-fat sync, token refresh, GoogleHealthAuthError propagation, non-null-only upsert, local-day bucketing.
- Newest-first early-stop must be correct: only stop after a FULL page has zero points newer-or-equal-to since (guards against a single old point mid-page).
`

phase('Build')
const build = await agent(
  `${CTX}\n\nImplement all deliverables. Read google_health.py + health_sync.py + the test file FIRST. Make the edits, then RUN the full verification yourself (cd apps/api && uv run ruff check . ; uv run ruff format . ; uv run mypy app ; uv run pytest -q) and fix any failures before finishing. Report files changed, the early-stop logic, and the final ruff/mypy/pytest output.`,
  { label: 'build', phase: 'Build' },
)

phase('Review')
const SCHEMA = {
  type: 'object', additionalProperties: false, required: ['findings'],
  properties: { findings: { type: 'array', items: {
    type: 'object', additionalProperties: false, required: ['file','severity','issue','fix'],
    properties: { file:{type:'string'}, severity:{type:'string',enum:['blocker','major','minor']}, issue:{type:'string'}, fix:{type:'string'} } } } },
}
const lenses = [
  'EARLY-STOP CORRECTNESS: verify pagination stops ONLY after a full page has zero points >= since (newest-first), never on a single mid-page old point; unparseable point times do NOT cause premature stop; since=None preserves full pagination; MAX_PAGES still caps. Verify each reader passes the RIGHT timestamp extractor (steps=interval.startTime, sleep=interval.endTime, heart-rate/hrv=sampleTime.physicalTime). Verify compute_since: None -> now-30d, else last_synced_at-2d.',
  'ORDERING + DATA SAFETY: verify `since` is captured from connection.last_synced_at BEFORE it is overwritten with _now(); _safe_read forwards since; upsert still writes only non-null fields (a metric missing from the window does not null a prior value); weight/body-fat unaffected; GoogleHealthAuthError still propagates.',
  'COMPILE + TESTS: verify ruff/mypy/pytest pass; types correct (datetime|None, Callable extractor); monkeypatched test readers accept since; the new early-stop unit test actually asserts page 3 is never fetched; no unused imports.',
]
const reviews = await parallel(lenses.map((l,i)=>()=>agent(`${CTX}\n\nImplementation done. Adversarially review by READING the changed files — find concrete real defects. ${l}\n\nOnly substantiated defects (cite file+snippet). Empty findings if clean.`, {label:`review#${i+1}`, phase:'Review', schema:SCHEMA})))
const findings = reviews.filter(Boolean).flatMap(r=>r.findings||[])
const blockers = findings.filter(f=>f.severity==='blocker'||f.severity==='major')

phase('Fix')
let fix='No blocker/major findings.'
if (blockers.length>0) fix = await agent(`${CTX}\n\nFix EACH blocker/major (Read first, minimal diff). Re-run cd apps/api && uv run ruff check . ; uv run ruff format . ; uv run mypy app ; uv run pytest -q and report results. No git.\n\nDEFECTS:\n${JSON.stringify(blockers,null,2)}`, {label:'fix', phase:'Fix'})

return { build, totalFindings: findings.length, blockers: blockers.length, findings, fix }
