# DB migration failure

A failed Alembic migration during deploy is one of the worst-case states
because the API may be partially down (the deploy script aborts before
swapping the api container, so the *old* api stays up — but if you're mid
incident, that's not always clear).

## Detect

The deploy script's `migrate` step (see `infra/scripts/app-deploy.sh`) runs
`alembic upgrade head` to completion via `docker compose run --rm migrate`.
If it exits non-zero, the deploy aborts. CI surfaces this as a failed
`deploy` job in `api-deploy.yml`.

Symptoms in the wild:

- `api-deploy.yml` deploy job failed; image was built and pushed but
  not swapped.
- Production is still serving the OLD image (good — schema unchanged).
- Discord notification fires `:x: API deploy failed`.

## Triage

1. **Pull the migration logs**:
   ```
   ssh ops@<host> sudo docker compose -f /etc/gymapp/app-compose.yml \
     logs --tail=200 gymapp-migrate
   ```
2. **Classify**:
   - SQL syntax error → revert the offending migration file, push.
   - Data constraint violation (e.g. NOT NULL on a column with NULLs) →
     restructure as two-step migration (see below).
   - Connection refused / timeout → Postgres is down, see incident runbook.
   - Alembic version mismatch ("Can't locate revision …") → see "version
     mismatch" below.

## Mitigation: rollback the deploy attempt

If the new image was published but the migration failed, the old image is
still running. You don't have to do anything to "roll back" — just block
the deploy:

1. Revert the offending commit:
   ```
   git revert <bad-sha>
   git push origin main
   ```
2. CI re-runs, picks up the reverted code, migrate is a no-op, api swaps.

## Mitigation: forward-fix a stuck migration

If the migration was partial (e.g. CREATE TABLE succeeded, then ALTER
failed), Alembic may think the version was applied but the schema is
inconsistent.

1. Verify current alembic state:
   ```
   ssh ops@<host> sudo docker exec gymapp-postgres \
     psql -U gym -d gym -c "SELECT version_num FROM alembic_version;"
   ```
2. Compare against the file in `apps/api/alembic/versions/` matching that
   version_num.
3. If the migration partially applied, write a NEW migration that
   completes the partial work (forward-fix) rather than trying to
   downgrade. Forward-fix is always safer than downgrade in production.

## Mitigation: roll back a migration

Avoid this when possible. If you must:

```
ssh ops@<host> sudo docker compose -f /etc/gymapp/app-compose.yml \
  run --rm migrate alembic downgrade -1
```

This runs the offending revision's `downgrade()`. If that function isn't
correct (or doesn't exist), you're in restore-from-backup territory:

```
# See restore.md for the full procedure.
ssh ops@<host> sudo /usr/local/bin/gymapp-pg-restore \
  /var/lib/gymapp/backups/daily/gym-$(date -u +%Y-%m-%d).sql.gz
```

This is destructive — it drops and recreates the gym database. Use
during a maintenance window.

## Two-step migration pattern

For destructive changes (drop column, change type, add NOT NULL to a
populated column), always ship in two PRs:

### PR 1: additive, deployable

- Add the new column / table / shape.
- App code reads from BOTH the old and new shape; writes to BOTH.
- Backfill the new shape (separate migration or one-shot script).
- Verify in prod for >24h.

### PR 2: drop the old shape

- Remove the old column / table.
- Remove the dual-read/write code.

This guarantees that a failed PR 2 deploy doesn't break production —
the app still works with both shapes in place.

## Version mismatch ("Can't locate revision X")

Usually means a developer reset their local DB and re-created a
migration with a different filename. Fix:

1. Identify the orphaned revision in alembic_version.
2. Either:
   - Edit `alembic_version.version_num` to point at a valid revision
     (only if the schema actually matches).
   - Restore from backup and re-apply all migrations.

Never delete from `alembic_version` without understanding the schema
state.
