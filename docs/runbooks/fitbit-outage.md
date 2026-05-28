# Fitbit outage

Fitbit's API is unreliable. The sync worker (07.01) and push worker (07.02)
both retry on transient errors but bow out on auth failures or sustained
rate limits. This runbook covers what to do when the `FitbitSyncErrorRateHigh`
alert fires or users report missing data.

## Verify

Check Fitbit's status page first:

- https://status.fitbit.com/

Then check our metrics:

```
ssh ops@<host> 'curl -sH "Authorization: Bearer ${METRICS_TOKEN}" http://127.0.0.1:8000/metrics | grep fitbit_sync_total'
```

Expected output (healthy):

```
fitbit_sync_total{outcome="success"} 1432.0
fitbit_sync_total{outcome="auth_failed"} 2.0
fitbit_sync_total{outcome="rate_limited"} 5.0
```

If `rate_limited` is climbing fast → Fitbit rate-limit issue. If
`auth_failed` is climbing → tokens are expiring and refresh is failing.

## Common causes

### 1. Fitbit-side outage

Nothing to do on our side. The sync worker keeps retrying; activities will
backfill when Fitbit recovers. Post in Discord:

```
:information_source: Fitbit API is currently degraded. Workout sync is
paused until Fitbit recovers; data will backfill automatically.
```

### 2. Rate limiting (HTTP 429)

Fitbit's limit is 150 requests/user/hour. Our worker uses
`Retry-After`-aware backoff (in `app/clients/fitbit.py::FitbitRateLimitedError`)
so this shouldn't happen in steady state.

If it does, check the cron interval:

```
ssh ops@<host> sudo systemctl list-timers | grep fitbit
```

The `fitbit_sync_all_periodic` cron fires every 30 min and pulls 14 days
of daily metrics + activities — that's ~30 API calls per sync per user.
With multiple users, you can hit the limit.

Mitigation: stretch the cron interval. In `app/workers/main.py`, change
`minute={0, 30}` to `hour=0,2,4,...` (every 2h). Deploy.

### 3. Token refresh failing

Check the API logs for auth errors:

```
ssh ops@<host> sudo docker logs --tail=500 gymapp-worker | grep -i fitbit
```

If you see "FitbitAuthError" repeatedly:

- A user revoked our app in Fitbit's settings → expected; user re-connects.
- Our app's client secret rotated → see [rotate-secrets](rotate-secrets.md).
- Fitbit's refresh token TTL changed → rare; check their changelog.

To force-reauth a single user:

```
ssh ops@<host> sudo docker exec -it gymapp-postgres psql -U gym -d gym \
  -c "DELETE FROM fitbit_connections WHERE user_id = '<user-uuid>';"
```

The user re-connects via the UI. Imported activities are kept.

### 4. Webhook subscriber paused

If Fitbit thinks our webhook endpoint is unreachable, they'll pause it
silently after repeated 5xx responses. Re-enable via the Fitbit dev portal
or `POST /api/v2/subscriptions/{collection}/{subscriberId}.json`.

## Push (07.02) failures

The push worker (`fitbit_push_session_task`) skips silently on 401/403 per
the design from 07.02. Workouts queue up locally; they don't retry until
the next finish. If you fixed the underlying auth issue, push will resume
on the next finished session — there's no per-session retry.

If you need to backfill a session you finished during the outage:

```
curl -X POST -H "Authorization: Bearer <token>" \
  https://api.<domain>/v1/workout-sessions/<session-id>/push-to-fitbit
```

## Verify recovery

```
ssh ops@<host> sudo systemctl start fitbit_sync_all_periodic.service
```

Wait 30s, then:

```
ssh ops@<host> 'curl -sH "Authorization: Bearer ${METRICS_TOKEN}" http://127.0.0.1:8000/metrics | grep fitbit_sync_total{outcome=\"success\"}'
```

The counter should have incremented.
