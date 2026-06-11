"""Dump the FastAPI OpenAPI spec without booting uvicorn or hitting the DB.

Usage:
    cd apps/api && uv run python -m scripts.export_openapi > ../../packages/openapi/openapi.json

CI uses this to detect drift between code and the committed spec.
"""

from __future__ import annotations

import json
import sys

from app.main import create_app


def main() -> int:
    app = create_app()
    spec = app.openapi()
    json.dump(spec, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
