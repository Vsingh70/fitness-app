#!/usr/bin/env bash
# Refresh apps/api/seed/exercises/ from upstream free-exercise-db (public domain).
# Re-run any time we want to pick up upstream additions or corrections.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_DIR="${SCRIPT_DIR}/../seed/exercises"
mkdir -p "${SEED_DIR}"

curl -fsSL https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json \
  -o "${SEED_DIR}/exercises.json"
curl -fsSL https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/LICENSE.md \
  -o "${SEED_DIR}/LICENSE.md"

echo "Wrote ${SEED_DIR}/exercises.json and LICENSE.md"
