#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "Starting local services (postgres, redis, ollama)..."
docker compose up -d --wait

echo ""
echo "Services up:"
docker compose ps

cat <<'EOF'

Next steps:
  1. apps/api:   cd apps/api  && uv sync && uv run uvicorn app.main:app --reload
  2. apps/web:   cd apps/web  && pnpm install && pnpm dev
  3. apps/ios:   open apps/ios in Xcode

Useful URLs:
  Postgres:  postgres://gym:gym@localhost:5433/gym
  Redis:     redis://localhost:6379
  Ollama:    http://localhost:11434

Stop everything with: scripts/dev-down.sh
EOF
