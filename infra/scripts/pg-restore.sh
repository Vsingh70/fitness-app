#!/usr/bin/env bash
#
# Restore a logical backup into the Postgres container.
#
# Usage:
#   pg-restore.sh <backup-file.sql.gz>
#
# The script:
# 1. Verifies the backup file exists and is non-empty.
# 2. Drops + recreates the target database (you'll be prompted to confirm).
# 3. Restores via psql.
#
# Intended for use on a SANDBOX VPS, not prod. Test restores monthly per the
# runbook in docs/runbooks/restore.md.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <backup-file.sql.gz>" >&2
  exit 2
fi

BACKUP_FILE="$1"
PG_CONTAINER="${PG_CONTAINER:-gymapp-postgres}"
PG_DB="${PG_DB:-gym}"
PG_USER="${PG_USER:-gym}"

if [ ! -s "${BACKUP_FILE}" ]; then
  echo "Backup file ${BACKUP_FILE} missing or empty" >&2
  exit 1
fi

echo "About to DROP and recreate database ${PG_DB} in ${PG_CONTAINER}."
read -r -p "Type 'restore' to confirm: " ack
if [ "${ack}" != "restore" ]; then
  echo "Aborted."
  exit 1
fi

echo "[pg-restore] dropping ${PG_DB}"
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d postgres -c \
  "DROP DATABASE IF EXISTS \"${PG_DB}\" WITH (FORCE);"
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d postgres -c \
  "CREATE DATABASE \"${PG_DB}\" OWNER \"${PG_USER}\";"

echo "[pg-restore] restoring from ${BACKUP_FILE}"
gunzip -c "${BACKUP_FILE}" | docker exec -i "${PG_CONTAINER}" \
  psql --quiet --set ON_ERROR_STOP=on -U "${PG_USER}" -d "${PG_DB}"

echo "[pg-restore] done"
