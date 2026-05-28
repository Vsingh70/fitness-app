#!/usr/bin/env bash
#
# Nightly Postgres logical backup.
#
# - Dumps the gymapp database via `docker exec gymapp-postgres pg_dump`.
# - Stores locally in $BACKUP_DIR with date-stamped filename.
# - rclone copy to B2 ($BACKUP_B2_REMOTE).
# - Prunes locally beyond retention windows. Remote prune is done by rclone's
#   bucket lifecycle rules (set when creating the bucket).
#
# Idempotent: re-running the same day overwrites the day's snapshot.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/lib/gymapp/backups}"
PG_CONTAINER="${PG_CONTAINER:-gymapp-postgres}"
PG_DB="${PG_DB:-gym}"
PG_USER="${PG_USER:-gym}"
B2_REMOTE="${B2_REMOTE:-b2:gymapp-backups}"
RETENTION_DAILY="${RETENTION_DAILY:-14}"
RETENTION_WEEKLY="${RETENTION_WEEKLY:-8}"
RETENTION_MONTHLY="${RETENTION_MONTHLY:-12}"

mkdir -p "${BACKUP_DIR}/daily" "${BACKUP_DIR}/weekly" "${BACKUP_DIR}/monthly"

today=$(date -u +%Y-%m-%d)
weekday=$(date -u +%u)        # 1..7 (Mon..Sun)
day_of_month=$(date -u +%d)

daily_path="${BACKUP_DIR}/daily/gym-${today}.sql.gz"

echo "[pg-backup] dumping to ${daily_path}"
docker exec -i "${PG_CONTAINER}" \
  pg_dump --clean --if-exists --no-owner --no-privileges -U "${PG_USER}" "${PG_DB}" \
  | gzip -9 > "${daily_path}.tmp"
mv "${daily_path}.tmp" "${daily_path}"

# Sunday → also keep a weekly snapshot.
if [ "${weekday}" = "7" ]; then
  cp -p "${daily_path}" "${BACKUP_DIR}/weekly/gym-${today}.sql.gz"
fi

# 1st of month → also keep a monthly snapshot.
if [ "${day_of_month}" = "01" ]; then
  cp -p "${daily_path}" "${BACKUP_DIR}/monthly/gym-${today}.sql.gz"
fi

# Local prune. find's -mtime is in days.
find "${BACKUP_DIR}/daily" -name "gym-*.sql.gz" -mtime +"${RETENTION_DAILY}" -delete
find "${BACKUP_DIR}/weekly" -name "gym-*.sql.gz" -mtime +"$(( RETENTION_WEEKLY * 7 ))" -delete
find "${BACKUP_DIR}/monthly" -name "gym-*.sql.gz" -mtime +"$(( RETENTION_MONTHLY * 31 ))" -delete

echo "[pg-backup] syncing to ${B2_REMOTE}"
rclone copy --quiet --update "${BACKUP_DIR}/daily" "${B2_REMOTE}/daily"
rclone copy --quiet --update "${BACKUP_DIR}/weekly" "${B2_REMOTE}/weekly"
rclone copy --quiet --update "${BACKUP_DIR}/monthly" "${B2_REMOTE}/monthly"

# node_exporter textfile collector: surface the unix timestamp of the most
# recent successful backup so prometheus can fire the BackupNotCompleted
# alert when it gets stale.
TEXTFILE_DIR="${TEXTFILE_DIR:-/var/lib/node_exporter/textfile_collector}"
if [ -d "${TEXTFILE_DIR}" ]; then
  cat > "${TEXTFILE_DIR}/backup.prom.tmp" <<EOF
# HELP gymapp_pg_backup_last_success_timestamp_seconds Unix time of the most recent successful pg-backup.
# TYPE gymapp_pg_backup_last_success_timestamp_seconds gauge
gymapp_pg_backup_last_success_timestamp_seconds $(date +%s)
EOF
  mv "${TEXTFILE_DIR}/backup.prom.tmp" "${TEXTFILE_DIR}/backup.prom"
fi

echo "[pg-backup] done"
