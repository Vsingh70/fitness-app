#!/usr/bin/env bash
#
# Roll the API back to a specific image tag (commit SHA or 'previous').
#
# Usage:
#   gymapp-app-rollback <sha>     # roll to ghcr.io/.../gym-api:<sha>
#   gymapp-app-rollback previous  # roll to whatever is in /etc/gymapp/previous-image
#
# Stores the prior `latest` digest in /etc/gymapp/previous-image so a quick
# `previous` rollback is one command. The deploy script writes that file at
# the start of every successful rollout.

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <sha|previous>" >&2
  exit 2
fi

target="$1"
COMPOSE="/etc/gymapp/app-compose.yml"
PREV_FILE="/etc/gymapp/previous-image"
HEALTH_URL="http://127.0.0.1:8000/v1/health/ready"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-90}"

# Resolve the image ref the deploy script wrote on previous successful rolls.
if [ "${target}" = "previous" ]; then
  if [ ! -s "${PREV_FILE}" ]; then
    echo "${PREV_FILE} is empty; no previous image recorded" >&2
    exit 1
  fi
  image_ref=$(cat "${PREV_FILE}")
else
  # Read the registry+repo from the current compose and substitute the tag.
  current=$(grep -E '^\s*image:\s*' "${COMPOSE}" | head -1 | awk '{print $2}')
  base="${current%:*}"
  image_ref="${base}:${target}"
fi

echo "[rollback] target image: ${image_ref}"

echo "[rollback] pulling ${image_ref}"
docker pull "${image_ref}"

# Re-tag as :latest so the compose file's `image: ...:latest` line picks it up.
latest_ref="${image_ref%:*}:latest"
docker tag "${image_ref}" "${latest_ref}"

echo "[rollback] re-running migrate (alembic upgrade head is idempotent)"
docker compose -f "${COMPOSE}" run --rm migrate

echo "[rollback] swapping api container"
docker compose -f "${COMPOSE}" up -d --no-deps --remove-orphans api

echo "[rollback] waiting up to ${HEALTH_TIMEOUT}s for ${HEALTH_URL}"
for i in $(seq 1 "${HEALTH_TIMEOUT}"); do
  if curl --silent --fail --max-time 2 "${HEALTH_URL}" >/dev/null; then
    echo "[rollback] api healthy after ${i}s"
    break
  fi
  sleep 1
done

if ! curl --silent --fail --max-time 2 "${HEALTH_URL}" >/dev/null; then
  echo "[rollback] ERROR: api did not become healthy" >&2
  docker compose -f "${COMPOSE}" logs --tail=200 api >&2 || true
  exit 1
fi

echo "[rollback] swapping worker"
docker compose -f "${COMPOSE}" up -d --no-deps worker

echo "[rollback] done; current image: ${image_ref}"
