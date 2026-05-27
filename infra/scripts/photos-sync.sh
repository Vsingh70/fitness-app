#!/usr/bin/env bash
#
# Hourly rclone sync of meal photos to B2. One-way (local → remote). Idempotent.

set -euo pipefail

LOCAL_DIR="${LOCAL_DIR:-/var/lib/gymapp/meal-photos}"
B2_REMOTE="${B2_REMOTE:-b2:gymapp-meal-photos}"

if [ ! -d "${LOCAL_DIR}" ]; then
  echo "Local dir ${LOCAL_DIR} does not exist; nothing to sync" >&2
  exit 0
fi

rclone sync --quiet --transfers 8 --checkers 16 \
  --b2-hard-delete=false \
  "${LOCAL_DIR}" "${B2_REMOTE}"
