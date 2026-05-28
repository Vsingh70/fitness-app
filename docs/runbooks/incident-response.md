# Incident response

A single-person service. The point of this runbook is to keep me from
freezing or skipping steps under pressure.

## Severity

| Sev | Definition | Response time |
| --- | ---------- | ------------- |
| sev0 | Total outage; nobody can log in or log a workout | drop everything, ack within 5 min |
| sev1 | Partial outage; major feature broken (Fitbit sync down, photo recognition down) | ack within 15 min, fix within 2h |
| sev2 | Degraded; latency spike, intermittent errors, one user affected | ack within 1h, fix same day |
| sev3 | Cosmetic or non-functional | normal backlog |

Alerts fired by Grafana map to sev as follows:
- `ApiDown`, `BackupNotCompleted` → sev0
- `ApiHighLatency`, `ApiHighErrorRate`, `OllamaDown` → sev1
- `FitbitSyncErrorRateHigh`, `PostgresDiskHigh` → sev2

## When an alert fires

1. **Acknowledge** in Discord (react with 👀 or reply "ack").
2. **Capture context** before touching anything:
   - Screenshot the Grafana panel that fired.
   - `gh run list -L 5` — has anything recently deployed?
   - `ssh ops@<host> sudo docker logs --tail=200 gymapp-api` — anything obvious?
3. **Stop the bleeding** if there's an obvious cause:
   - Recent deploy looks bad → `gymapp-app-rollback previous`.
   - Ollama wedged → see [ollama-down runbook](ollama-down.md).
   - Fitbit-side issue → see [fitbit-outage runbook](fitbit-outage.md).
   - DB disk full → free space first (drop old `fitbit_activities` raw payloads, vacuum), then plan resize.
4. **Communicate** in Discord:
   - "Investigating: <one-line summary>" within the ack SLA.
   - "Mitigated: <what changed>" once traffic recovers.
   - "Resolved: <root cause + follow-ups>" once the system is fully stable.
5. **Postmortem** if sev0/sev1:
   - Add an entry to the "Past incidents" section of `deploy.md`.
   - Note: timestamp, trigger, mitigation, root cause, follow-up tasks.

## Quick-reference commands

```
# Health
curl -fs https://api.<domain>/v1/health/ready
ssh ops@<host> sudo systemctl status gymapp-app gymapp-postgres gymapp-redis ollama caddy

# Logs
ssh ops@<host> sudo docker logs --tail=200 -f gymapp-api
ssh ops@<host> sudo docker logs --tail=200 -f gymapp-worker
ssh ops@<host> sudo journalctl -u gymapp-app-deploy.service --no-pager -n 200

# Rollback
ssh ops@<host> sudo /usr/local/bin/gymapp-app-rollback previous

# DB shell (read-only mindset; do NOT run DDL or DELETE without a vetted plan)
ssh ops@<host> sudo docker exec -it gymapp-postgres psql -U gym -d gym
```

## Comms script (template)

```
:warning: Investigating: <product impact, e.g. "users can't log workouts">
Detected via: <alert name or external report>
Timeline:
- HH:MM UTC - alert fired
- HH:MM UTC - investigation started
Will update in 15 min.
```

```
:white_check_mark: Mitigated: <what changed, e.g. "rolled back to deploy abc123">
Cause still under investigation; full RCA tomorrow.
```

```
:closed_book: Resolved: <one-line root cause>
Follow-ups:
- [ ] task 1
- [ ] task 2
```
