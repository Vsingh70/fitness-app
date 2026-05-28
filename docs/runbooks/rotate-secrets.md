# Rotate secrets

All secrets live in three places that must stay in sync:

1. **1Password vault** — source of truth.
2. **GitHub Actions secrets** — used by CI/CD.
3. **Ansible Vault** (`infra/ansible/group_vars/vault.yml`) — used by the VPS.

Rotation cadence:

| Secret | Cadence | Notes |
| ------ | ------- | ----- |
| `JWT_SECRET` | quarterly OR on suspected leak | rotating invalidates ALL access tokens; users re-auth on next request |
| `FITBIT_CLIENT_SECRET` | only when forced by Fitbit | requires re-registering the OAuth app |
| `FITBIT_TOKEN_KEY` | only on suspected leak | rotating drops every stored Fitbit access/refresh token |
| `MEAL_PHOTO_SIGNING_SECRET` | only on suspected leak | invalidates outstanding signed URLs (clients re-request) |
| `APPLE_BUNDLE_IDS` / `GOOGLE_CLIENT_IDS` | when adding/removing a client | additive — append the new id, deploy, then remove the old after 30d |
| `POSTGRES_PASSWORD` | yearly | DB is private-IP only; pressure is low |
| `B2_APPLICATION_KEY` | when the laptop with the key is lost | regenerate in B2 console |
| `DEPLOY_SSH_KEY` | yearly OR on team change | `ssh-keygen -t ed25519` new pair, add to `~/.ssh/authorized_keys` first, then update Actions secret, then remove old key |
| `METRICS_TOKEN` | yearly | rotating drops Grafana scraping until the datasource is updated |
| `DISCORD_WEBHOOK_URL` | when channel changes | low-stakes |

## General procedure

1. **Generate** the new value:
   ```
   openssl rand -hex 32      # for opaque secrets (JWT, signing keys, METRICS_TOKEN)
   ssh-keygen -t ed25519 -C ops@gymapp-deploy -f /tmp/gymapp-deploy   # for SSH
   ```
2. **Store** in 1Password (overwrite the existing item, do NOT delete the old).
3. **Update GitHub**:
   ```
   gh secret set JWT_SECRET --body "..."
   ```
4. **Update Ansible Vault**:
   ```
   cd infra/ansible
   ansible-vault edit group_vars/vault.yml
   ```
5. **Deploy** so the new value takes effect:
   - GitHub-only changes (e.g. `DEPLOY_SSH_KEY`): next push picks it up.
   - VPS-side changes (`POSTGRES_PASSWORD`, `JWT_SECRET`, `FITBIT_*`, `METRICS_TOKEN`, photo signing): `ansible-playbook site.yml --ask-vault-pass` to re-render `/etc/gymapp/app.env`, then `systemctl restart gymapp-app.service`.
6. **Verify**:
   - For `JWT_SECRET`: log in with a test account, verify access token works.
   - For `FITBIT_TOKEN_KEY`: connect a Fitbit account, run a manual sync, verify the connection row decrypts.
   - For `METRICS_TOKEN`: update the Grafana Prometheus datasource → Test → 200.
   - For `DEPLOY_SSH_KEY`: trigger a manual deploy → see successful SSH step.
7. **Retire** the old value:
   - For SSH keys: remove from `~ops/.ssh/authorized_keys` on the VPS.
   - For other secrets: archive the previous version in 1Password and mark "retired YYYY-MM-DD".

## Special: JWT_SECRET

Rotating `JWT_SECRET` invalidates every access token. To minimize user
impact:

1. Roll out a deploy that accepts BOTH the old AND new secret (multi-key
   validation). **Not implemented yet** — current code only validates against
   one secret. If you rotate JWT_SECRET today, every user is logged out.
2. As a workaround until multi-key lands: rotate during low-traffic hours
   and announce in the Discord channel.

Tracked work to make this seamless: TODO add `JWT_SECRET_PREVIOUS` env var
support in `app/services/auth.py::verify_access_token`.

## Special: FITBIT_TOKEN_KEY

`FITBIT_TOKEN_KEY` decrypts the tokens stored in `fitbit_connections`.
Rotating it makes every existing row's `access_token_encrypted` and
`refresh_token_encrypted` undecryptable. The next sync for that user will:

1. Call `secretbox.decrypt()` → raise `DecryptionError`
2. Skip the sync silently (per the OAuth service's failure path)
3. Surface as "connection broken" on the next status check

Users will need to re-connect Fitbit. Don't do this routinely. If you must:

1. Take a Postgres backup first (`gymapp-pg-backup` manually).
2. Truncate `fitbit_connections` so users get a clean "not connected" state.
3. Rotate the key and deploy.
4. Notify affected users.
