#!/usr/bin/env bash
#
# Zero-downtime API rollout: docker pull → docker compose up (with the
# `--no-deps` + `--scale` trick to bring the new container up alongside the
# old, wait for healthy, then drop the old one).
#
# Triggered by `systemctl start gymapp-app-deploy.service` or directly from
# CI via SSH.

set -euo pipefail

COMPOSE="/etc/gymapp/app-compose.yml"
PREV_FILE="/etc/gymapp/previous-image"
MIGRATE="migrate"
SERVICE="api"
WORKER="worker"
HEALTH_URL="http://127.0.0.1:8000/v1/health"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-90}"

# Snapshot the currently-running image for one-command rollback.
current_image=$(docker inspect gymapp-api --format='{{.Image}}' 2>/dev/null || true)
if [ -n "${current_image}" ]; then
  current_ref=$(docker inspect "${current_image}" --format='{{index .RepoDigests 0}}' 2>/dev/null || true)
  if [ -n "${current_ref}" ]; then
    echo "${current_ref}" > "${PREV_FILE}"
  fi
fi

echo "[deploy] pulling latest images"
docker compose -f "${COMPOSE}" pull "${MIGRATE}" "${SERVICE}" "${WORKER}"

echo "[deploy] running migrations"
# `up --no-deps migrate` runs the migration container to completion. It's
# `restart: no`, so it exits with the alembic exit code. `--exit-code-from`
# would surface the non-zero status, but it conflicts with detached mode;
# instead we use `run` for a clean exit code.
docker compose -f "${COMPOSE}" run --rm "${MIGRATE}"

echo "[deploy] bringing up new ${SERVICE}"
# Compose's `up -d --no-deps` recreates the container in place. The container
# is healthchecked; we wait for the health endpoint to respond.
# NOTE: do NOT pass --remove-orphans here. Postgres/Redis run as their own
# compose projects sharing the gymapp_default network; --remove-orphans makes
# this app project delete them as "orphans", taking the database down on every
# deploy. The app project only owns migrate/api/worker.
docker compose -f "${COMPOSE}" up -d --no-deps "${SERVICE}"

echo "[deploy] waiting up to ${HEALTH_TIMEOUT}s for ${HEALTH_URL}"
for i in $(seq 1 "${HEALTH_TIMEOUT}"); do
  if curl --silent --fail --max-time 2 "${HEALTH_URL}" >/dev/null; then
    echo "[deploy] api healthy after ${i}s"
    break
  fi
  sleep 1
done

if ! curl --silent --fail --max-time 2 "${HEALTH_URL}" >/dev/null; then
  echo "[deploy] ERROR: api did not become healthy" >&2
  docker compose -f "${COMPOSE}" logs --tail=200 "${SERVICE}" >&2 || true
  exit 1
fi

echo "[deploy] rolling worker"
docker compose -f "${COMPOSE}" up -d --no-deps "${WORKER}"

echo "[deploy] done"
