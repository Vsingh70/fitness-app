# Launch runbook — manual, non-agent-actionable items

These are the TODO.md items that require provisioning real infrastructure,
creating third-party accounts, or a Mac with Xcode. A coding agent cannot do
any of them. Run them in this order — later steps assume earlier ones.

Cross-reference: each step cites the TODO.md ID and the canonical spec under
`tasks/09-deployment/`.

---

> **How this repo actually deploys.** `.github/workflows/api-deploy.yml`
> already runs the full CD loop on every push to `main`: build image →
> push to GHCR → SSH to the VPS → `infra/scripts/app-deploy.sh` (pull →
> migrate → zero-downtime swap) → Discord ping. The deploy job is gated by
> `if: vars.DEPLOY_ENABLED == 'true'`, so until you flip that variable it
> only builds-and-pushes. The host's app secrets come from **ansible-vault**
> (`group_vars/vault.yml`), NOT a hand-edited `/etc/gymapp/app.env` — the
> `app` role templates `app.env` and `app-compose.yml` onto the host for you.
> The reverse proxy is **Caddy**, configured by the `nginx` role
> (`roles/nginx/templates/Caddyfile.j2`); TLS is automatic once DNS resolves.

## Phase A — Stand up the host (do first; everything else needs it)

### A1. Hetzner VPS — DEPLOY-1 (`tasks/09-deployment/01-vps-provisioning.md`)
1. Create a Hetzner Cloud CX22 (2 vCPU / 4 GB) in `eu-central` or `us-east`.
   Add your SSH key at create time so the first (root) login works.
2. **Inventory** — copy the example and edit it (the real file is gitignored):
   ```bash
   cp infra/ansible/inventory.ini.example infra/ansible/inventory.ini
   ```
   Set `ansible_host=<VPS_IP>`, `app_domain=<your api domain>`,
   `app_letsencrypt_email=<you>`. `ansible_user=ops` is correct — the very
   first run overrides it with `-u root` (the `base` role creates `ops`).
3. **Non-secret vars** — in `infra/ansible/group_vars/all.yml`, set
   `app_image` to your **lowercase** GHCR path
   (`ghcr.io/<owner>/gymapp-api:latest`). Defaults for postgres/redis/ollama/
   backup/monitoring are already sane; override only if needed.
4. **Secrets vault** — this is where ALL app/DB/Fitbit/B2 secrets live
   (see the A2 checklist below). Copy, fill every `CHANGE_ME`, then encrypt:
   ```bash
   cp infra/ansible/group_vars/vault.yml.example infra/ansible/group_vars/vault.yml
   # edit vault.yml ...
   ansible-vault encrypt infra/ansible/group_vars/vault.yml
   ```
5. **Run the playbook** (install Galaxy roles first; first run as root):
   ```bash
   ansible-galaxy install -r infra/ansible/requirements.yml
   ansible-playbook -i infra/ansible/inventory.ini infra/ansible/site.yml \
     -u root --ask-vault-pass
   ```
   Subsequent runs drop `-u root` (use the `ops` user).
6. **Verify roles applied** — SSH in (`ssh ops@<VPS_IP>`) and check:
   - `docker ps` shows postgres, redis, ollama, api, worker, caddy
   - `systemctl status node_exporter promtail` (monitoring role)
   - base hardening: root SSH disabled, `ops` user exists, swap on
   - the `app` role wrote `/etc/gymapp/app-compose.yml` and `/etc/gymapp/app.env`
7. **Validate registry auth** by pulling one image manually:
   ```bash
   docker login ghcr.io        # PAT with read:packages
   docker pull ghcr.io/<owner>/gymapp-api:latest   # owner must be lowercase
   ```
   > GHCR refs are case-sensitive and must be lowercase.

### A2. Vault fill-in checklist — what each secret is and where it comes from
Fill these in `group_vars/vault.yml` before encrypting (step A1.4):

| Vault key | Value / how to get it |
|---|---|
| `vault_postgres_password` | `openssl rand -hex 24` |
| `vault_app_jwt_secret` | `openssl rand -hex 64` (64-byte hex) |
| `vault_app_apple_bundle_ids` | your iOS + web bundle ids, comma-separated |
| `vault_app_google_client_ids` | Google OAuth client id(s) — allowed audiences |
| `vault_app_fitbit_client_id` / `_secret` | Fitbit dev app (dev.fitbit.com) |
| `vault_app_fitbit_token_key` | `openssl rand -hex 32` (encrypts stored tokens) |
| `vault_app_fitbit_webhook_signing_secret` | from the Fitbit subscriber config |
| `vault_app_fitbit_webhook_subscriber_verification` | Fitbit subscriber verification code |
| `vault_app_meal_photo_signing_secret` | `openssl rand -hex 32` |
| `vault_b2_application_key_id` / `_key` / `_bucket` | Backblaze B2 app key + bucket |
| `vault_loki_username` / `_password` | Grafana Cloud → Loki data source creds |

> `JWT_SECRET_PREVIOUS` (API-3 rotation) is intentionally absent on first
> deploy — add it only during a rotation (Phase E / OPS-2), per
> `docs/runbooks/rotate-secrets.md`.

### A3. Domain + Caddy TLS — OPS-3
1. Point an A record for `<app_domain>` at the VPS IP.
2. Wait for Caddy to issue the cert (`docker logs caddy` on the host).
3. Verify chain + HSTS:
   ```bash
   curl -vk https://<app_domain>/   # valid chain + Strict-Transport-Security
   ```

---

## Phase B — GitHub Actions config (DEPLOY-2)

App secrets already live in the vault (Phase A). GitHub Actions only needs
what CI uses to **reach** the host and notify — nothing app-internal.

### B1. Repo **secrets** (Settings → Secrets and variables → Actions)
- `DEPLOY_HOST` — VPS IP/hostname
- `DEPLOY_USER` — `ops`
- `DEPLOY_SSH_KEY` — private key for the `ops` deploy user
- `DISCORD_WEBHOOK_URL` — deploy + alert pings (create the channel first, OPS-4)
- iOS bundle secrets — deferred to Phase F

> Note: GHCR auth uses the built-in `GITHUB_TOKEN` (the build job logs in as
> `github.actor`), so no PAT secret is needed for CI pushes. B2 keys live in
> the vault (host-side backups), not in Actions.

### B2. Repo **variables**
- `APP_DOMAIN` — e.g. `api.example.com` (used for the smoke-test URL + env)
- `DEPLOY_ENABLED` — **leave UNSET until DEPLOY-4.** The deploy job is
  `if: vars.DEPLOY_ENABLED == 'true'`; setting it to `true` is what arms CD.

### OPS-4. Discord alerts channel (do before B1 so the webhook exists)
Create a private `gymapp-alerts` channel → Integrations → Webhooks → copy the
URL into `DISCORD_WEBHOOK_URL` (GitHub secret here + Grafana in Phase D).

---

## Phase C — Frontend deploy (DEPLOY-3)
1. Connect the GitHub repo to a new Vercel project.
2. Root directory: `apps/web`.
3. Build command:
   `pnpm install --frozen-lockfile && pnpm openapi:generate && pnpm build`
4. Env: `NEXT_PUBLIC_API_URL = https://<APP_DOMAIN>`.
5. `apps/web/vercel.json` is auto-detected on connect.

---

## Phase D — First deploy + observability wiring

### D1. End-to-end deploy + smoke test — DEPLOY-4
1. **Arm CD**: set the GitHub Actions **variable** `DEPLOY_ENABLED=true`
   (only now that the host accepts SSH — this is the gate from B2).
2. Push a no-op commit to `main` (or re-run the latest `api-deploy.yml`).
3. Watch `api-deploy.yml`: build → push → SSH → `app-deploy.sh`
   (pull → `run --rm migrate` → zero-downtime swap) → Discord ping.
4. Smoke:
   ```bash
   curl https://<APP_DOMAIN>/v1/health    # 200
   curl https://<APP_DOMAIN>/v1/auth/dev         # JWT, only if ENV != prod
   ```
5. Rollback drill: `gymapp-app-rollback previous` on the host; confirm it swaps
   back. (`infra/scripts/app-deploy.sh`, `app-rollback.sh`.)

### D2. Grafana Cloud + Discord alerts — OBS-2 (`tasks/09-deployment/03-observability.md`)
1. Create a free Grafana Cloud account.
2. Import dashboards from `infra/grafana/dashboards/`.
3. Import alerts from `infra/grafana/alerts/`.
4. Point alert delivery at `DISCORD_WEBHOOK_URL`.
5. Fire-test: temporarily set `BackupNotCompleted` window to `1m`, confirm a
   Discord ping, then revert.

### D3. BetterStack synthetic monitor — OBS-3 (`infra/synthetic/`)
1. Create a BetterStack account, import the monitor template.
2. Targets: `https://<APP_DOMAIN>/v1/health` and `/v1/health/live`.
3. Pipe alerts to the same Discord webhook.

### D4. Loki label hygiene — OBS-5
After logs flow, confirm no high-cardinality labels:
```bash
logcli labels                     # should NOT list user_id or request_id
logcli labels user_id 2>&1 | head # expect empty / not a label
```
Those fields belong in the log line, not the label set.

### D5. SLO dashboard — OBS-6
Add a Grafana dashboard: API availability over 28d (target 99.5%), p99 on
`/v1/workouts/sessions` and `/v1/foods/search` (< 500 ms), background-job lag
(< 5 min). Add burn-rate alerts at 2h and 24h windows.

---

## Phase E — Operational drills (after the app is live)

### OPS-1. Backup restore drill
Run `infra/scripts/pg-restore.sh` against a throwaway container or staging DB,
confirm it restores, and record the elapsed time in `docs/runbooks/restore.md`.

### OPS-2. Secret rotation drill (needs API-3 landed first)
Follow `docs/runbooks/rotate-secrets.md`:
- Rotate `JWT_SECRET` — set the old value as `JWT_SECRET_PREVIOUS` so sessions
  survive (this is exactly what API-3 enables).
- Rotate `METRICS_TOKEN`; confirm Grafana/Prometheus scraping still works.
- Rotate the deploy SSH key; confirm CI still ships.

---

## Phase F — iOS distribution (deferred; needs a Mac + Xcode 16) — OPS-5
1. Apple Developer Program enrollment ($99/yr).
2. App Store Connect app record (bundle id `com.virajsingh.gymapp`).
3. TestFlight group for buddies.
4. `match` repo for fastlane signing.
5. iOS build/CD already exists: `.github/workflows/ios-release.yml`,
   `apps/ios/fastlane/Fastfile`. Then work through `tasks/08-ios/` specs and
   apply the editorial guide `tasks/claude-code-editorial-ios.md`.

---

## Dependency order at a glance
```
A1 VPS ──▶ A3 DNS/TLS ──▶ B secrets/env ──▶ C Vercel ──▶ D1 first deploy
                                              │                 │
                                              └──▶ D2 Grafana ◀─┘──▶ D3 synthetic
                                                       │
                                                       └──▶ D4 Loki ──▶ D5 SLO
D1 ──▶ OPS-1 restore drill
API-3 (code) ──▶ OPS-2 rotation drill
(independent, anytime once you have a Mac) ──▶ Phase F iOS
```
