# Restore runbook

When to use this:

- Production database is corrupt or accidentally dropped.
- You need to spin up a sandbox VPS with a copy of yesterday's data.
- Monthly disaster-recovery drill (last Friday of the month).

## Prereqs

- A target host with the [09.01 provisioning](../../infra/README.md) applied.
  This brings up Postgres + the app container but with an empty DB.
- `rclone` configured with the `b2` remote and the application key from
  Ansible Vault (`vault_b2_application_key_id` / `vault_b2_application_key`).
- The latest backup downloaded locally:

  ```
  rclone copy b2:gymapp-backups/daily/gym-$(date -u +%Y-%m-%d).sql.gz ./
  ```

## Steps

1. SSH to the target host as `ops`.

2. Stop the API + worker so they don't write to the database during restore:

   ```
   sudo systemctl stop gymapp-app.service
   ```

3. Copy the backup file to the host:

   ```
   scp gym-YYYY-MM-DD.sql.gz ops@<host>:/tmp/
   ```

4. Run the restore script (it will prompt for confirmation):

   ```
   sudo /usr/local/bin/gymapp-pg-restore /tmp/gym-YYYY-MM-DD.sql.gz
   ```

   The script DROPs and recreates the `gym` database, then loads the dump.
   This takes ~30-60s on a CCX33 with realistic data.

5. Verify the schema is at the expected migration:

   ```
   sudo docker exec gymapp-postgres psql -U gym -d gym \
     -c "SELECT version_num FROM alembic_version;"
   ```

6. Start the API and check `/v1/health/ready`:

   ```
   sudo systemctl start gymapp-app.service
   curl -fs https://api.<your-domain>/v1/health/ready
   ```

## Sandbox restore (DR drill)

Same as the production restore, but on a dedicated sandbox VPS. Run a
spot-check after restore:

```
sudo docker exec gymapp-postgres psql -U gym -d gym -c "
  SELECT
    (SELECT COUNT(*) FROM workout_sessions) AS sessions,
    (SELECT COUNT(*) FROM meals) AS meals,
    (SELECT MAX(started_at) FROM workout_sessions) AS latest_session;
"
```

The numbers should match what you observed on prod yesterday. Document the
restore time in the team log and tear the sandbox down once verified.

## Photo restore

Meal photos are synced separately to a bucket. Restore with:

```
rclone copy b2:gymapp-meal-photos/ /var/lib/gymapp/meal-photos/
sudo chown -R ops:ops /var/lib/gymapp/meal-photos
```

The signed URL secret must match the one in `app.env`; if you restored to a
sandbox with a different secret, the previously-signed URLs will be invalid.
This is expected: clients re-sign on next read.

## Last-resort: load into a local Docker

If the production Postgres is wedged and you can't get a shell, you can load
the dump into a throwaway local Postgres for triage:

```
docker run -d --name pg-triage -e POSTGRES_PASSWORD=triage -p 5439:5432 postgres:16
gunzip -c gym-YYYY-MM-DD.sql.gz | docker exec -i pg-triage psql -U postgres
psql -h localhost -p 5439 -U postgres -d gym
```

Be careful: the dump is privileged data. Treat the laptop you load it on as
sensitive.
