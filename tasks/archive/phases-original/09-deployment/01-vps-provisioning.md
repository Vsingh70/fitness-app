# 09.01 VPS provisioning

## Context

Single Hetzner VPS hosts: API, Postgres, Redis, Ollama (text + vision models), nginx, and the meal photo storage volume.

## Goal

Reproducible provisioning of the VPS with infrastructure-as-code.

## Choice

Hetzner CCX33 or higher (dedicated vCPU, 8+ GB RAM for Ollama). Storage volume for photos and Postgres data (separate from boot disk).

## Provisioning

Use a single Ansible playbook in `infra/ansible/`:

- Roles:
  - `base`: ufw, fail2ban, unattended-upgrades, swap, ntpd, non-root user, ssh hardening.
  - `docker`: install Docker + compose plugin.
  - `postgres`: run Postgres 16 in Docker, persistent volume, daily logical backup to a separate bucket (B2 or Backblaze).
  - `redis`: run Redis 7 in Docker with AOF persistence.
  - `ollama`: install Ollama natively (better GPU access if added later), pull `qwen2.5:7b-instruct` and `llava-llama3:8b`.
  - `app`: pull the API container, run via systemd unit that does a docker pull + restart on `app-deploy` signal.
  - `nginx`: reverse proxy with TLS via Caddy or nginx + certbot.
  - `monitoring`: install node_exporter + a Promtail agent shipping logs to Grafana Cloud or a self-hosted Loki.

- Inventory checked into the repo (no secrets). Secrets in Ansible Vault.

## Backups

- Postgres: nightly `pg_dump` -> Backblaze B2. Keep 14 daily, 8 weekly, 12 monthly.
- Photo storage: rclone sync to B2 hourly.
- Restore runbook documented in `docs/runbooks/restore.md`.

## Deliverables

1. Ansible playbook with all roles.
2. Caddy or nginx config with HTTPS to `api.<domain>`.
3. Backup scripts in `infra/scripts/`.
4. Restore runbook tested at least once.
5. `infra/README.md` explaining how to provision a new VPS from scratch.

## Acceptance criteria

- Running `ansible-playbook site.yml` on a fresh server reaches a working state with API reachable on HTTPS.
- Pulling the latest API container with `app-deploy` rolls without dropping requests.
- A test restore of yesterday's backup into a sandbox VPS reproduces the data.

## Dependencies

None (can run in parallel with feature tasks once the API container is buildable).

## Out of scope

- Kubernetes (overkill for this scale).
- Multi-region (unnecessary).
