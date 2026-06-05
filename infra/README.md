# Infrastructure

Single-VPS deployment of the gymapp stack on Hetzner. Ansible-driven, all
declarative.

## Layout

```
infra/
  ansible/             # site.yml, roles/, group_vars/, inventory
  scripts/             # backup + deploy helpers (copied to /usr/local/bin)
docs/runbooks/         # restore.md, deploy.md
```

The playbook installs and runs:

| Component   | How                                         |
| ----------- | ------------------------------------------- |
| Postgres 16 | Docker compose, persistent volume, daily backup → B2 |
| Redis 7     | Docker compose, AOF persistence             |
| Ollama      | Native install via `install.sh`, models pulled at provision time |
| API + worker| Docker compose, systemd unit per service    |
| Caddy       | Native, auto-TLS via Let's Encrypt          |
| Monitoring  | node_exporter + Promtail (ships to Grafana Cloud / Loki) |
| Security    | ufw + fail2ban + unattended-upgrades + SSH hardening |

## Provision a fresh VPS

### Prereqs

- A Hetzner CCX33 (or larger). 8+ GB RAM required for Ollama with both
  `qwen2.5:7b-instruct` and `llava-llama3:8b` resident.
- A volume attached for `/var/lib/gymapp` (Postgres data + meal photos +
  backups). Mount before running Ansible.
- DNS A record for `api.<your-domain>` pointing at the VPS.
- An SSH key authorized for `root` on the VPS (Hetzner asks for one when
  creating the server).
- Local tools: `ansible-core`, `ansible-galaxy`, `rclone` (for verifying
  B2 credentials).

### Steps

1. **Install Ansible collections**

   ```
   cd infra/ansible
   ansible-galaxy collection install -r requirements.yml
   ```

2. **Copy and edit inventory**

   ```
   cp inventory.ini.example inventory.ini
   $EDITOR inventory.ini    # fill in ansible_host, app_domain, etc.
   ```

3. **Create the vault**

   ```
   cp group_vars/vault.yml.example group_vars/vault.yml
   $EDITOR group_vars/vault.yml         # fill in secrets
   ansible-vault encrypt group_vars/vault.yml
   ```

   Save the vault password somewhere safe (a password manager, or
   `--vault-password-file` pointed at a chmod-600 file).

4. **First run (as root)** — the `base` role creates the `ops` user and
   hardens SSH; subsequent runs go through `ops`.

   ```
   ansible-playbook -u root site.yml --ask-vault-pass
   ```

5. **Subsequent runs** — once the `ops` user exists with your SSH key:

   ```
   ansible-playbook site.yml --ask-vault-pass
   ```

6. **Verify**

   ```
   curl -fs https://api.<your-domain>/v1/health
   ```

## Backups

- Postgres: nightly logical dump at 01:30 UTC, gzipped, rclone-synced to
  `b2:gymapp-backups`. Retention: 14 daily + 8 weekly + 12 monthly locally;
  remote prune via B2 lifecycle rules on the bucket.
- Meal photos: hourly `rclone sync` to `b2:gymapp-meal-photos`. Add a cron
  manually if not yet set:

  ```
  echo "0 * * * * root /usr/local/bin/gymapp-photos-sync >> /var/log/gymapp-photos-sync.log 2>&1" \
    | sudo tee /etc/cron.d/gymapp-photos-sync
  ```

  (The `photos-sync.sh` script is intentionally not scheduled by the
  playbook so you can decide whether B2 sync is needed — most setups want
  it, but a dev VPS doesn't.)

## Deploy a new API image

See [`docs/runbooks/deploy.md`](../docs/runbooks/deploy.md).

## Restore from backup

See [`docs/runbooks/restore.md`](../docs/runbooks/restore.md). Practice
this monthly.

## Updating roles

```
ansible-lint roles/
ansible-playbook --syntax-check site.yml
ansible-playbook --check --diff site.yml --ask-vault-pass   # dry run
```

## What lives where on the box

| Path                              | Owner       |
| --------------------------------- | ----------- |
| `/var/lib/gymapp/postgres/`       | Postgres    |
| `/var/lib/gymapp/redis/`          | Redis       |
| `/var/lib/gymapp/meal-photos/`    | API (uid `ops`) |
| `/var/lib/gymapp/backups/`        | root (cron) |
| `/var/lib/ollama/`                | ollama user |
| `/etc/gymapp/*-compose.yml`       | systemd     |
| `/etc/gymapp/app.env`             | root, 0600  |
| `/etc/systemd/system/gymapp-*`    | systemd     |
| `/usr/local/bin/gymapp-*`         | scripts     |
| `/etc/caddy/Caddyfile`            | caddy       |

## Risks + things to check before going live

- **Vault**: rotate `vault_app_jwt_secret` and `vault_app_fitbit_token_key`
  before first user signs in. Default values in the example are placeholders.
- **DB password**: `vault_postgres_password` must be set; the role won't
  start Postgres with the example value.
- **Ollama disk**: models are large (~5 GB each). Verify the volume has
  >20 GB free before pulling.
- **Fitbit redirect URI**: must match what's configured in the Fitbit dev
  portal exactly.
- **B2 lifecycle**: configure bucket-level lifecycle rules to prune backups
  beyond ~13 months. The script's `find -mtime` only prunes the local copy.
