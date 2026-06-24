# 09.03 Observability, secrets, and runbooks

## Context

Once data starts flowing, we need to see what's happening, get alerted when something breaks, and know how to respond.

## Goal

A baseline observability stack and the runbooks needed for the system to be operated by one person.

## Observability

### Logs
- API logs JSON via structlog -> stdout -> Promtail -> Grafana Loki (Grafana Cloud free tier or self-hosted).
- Web logs from Vercel -> a Logflare or Axiom integration.

### Metrics
- API exposes Prometheus metrics at `/metrics` (auth-gated by a static token).
- node_exporter on the VPS for system metrics.
- Postgres exporter.
- Redis exporter.
- Ollama latency tracked via app-level metrics.
- Dashboards in Grafana for:
  - API latency p50/p95/p99 per route.
  - Postgres connections, slow queries, replication lag (n/a yet).
  - Ollama: queue depth, latency, model memory.
  - Fitbit sync: success/failure ratio, rate limit hits.

### Tracing
- OpenTelemetry from FastAPI -> Tempo (self-hosted) or Honeycomb (free tier).
- Sample at 10% baseline, 100% on errors.

### Alerts (Grafana Alerting)
- API p95 latency > 800ms for 5 minutes.
- API error rate > 2% for 5 minutes.
- Postgres disk usage > 80%.
- Ollama down (probe failing).
- Fitbit sync error rate > 10% over the last hour.
- Daily backup did not complete.

Alerts go to a Discord webhook and an email.

## Secrets

- All API secrets in 1Password or Bitwarden, mirrored to GitHub Actions secrets and Ansible Vault.
- Rotation runbook: API JWT secret, Fitbit client secret, Apple/Google credentials.

## Runbooks (in `docs/runbooks/`)

- `incident-response.md`: severity definitions, comms script.
- `restore-from-backup.md`: step-by-step.
- `rotate-secrets.md`: per-secret procedure.
- `ollama-down.md`: how to verify, restart, fall back to template rationales.
- `fitbit-outage.md`: when Fitbit's API is down or rate-limiting hard.
- `db-migration-failure.md`: how to roll back a migration safely.

## Deliverables

1. Prometheus + Grafana set up (self-hosted next to API, or Grafana Cloud).
2. Dashboards committed to `infra/grafana/` as JSON.
3. Alert rules committed.
4. All runbooks written.
5. Synthetic check from an external service (UptimeRobot or BetterStack) hitting `/v1/health` every minute.

## Acceptance criteria

- Latency dashboard reflects API requests within 30s of completion.
- Killing the API container triggers an alert in under 2 minutes.
- A simulated restore against the latest backup completes successfully.

## Dependencies

- `09.01 VPS provisioning`

## Out of scope

- SOC 2 controls or formal compliance (not needed for friends-and-family scope).
