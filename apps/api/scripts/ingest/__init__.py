"""Self-hosted food-data ingest (USDA FoodData Central + Open Food Facts).

These scripts bulk-load free food datasets into the ``foods`` table so the app
can search and resolve barcodes locally with no paid provider. They are designed
to run on the VPS (see ``docs/runbooks/food-data-refresh.md``).

Modules:
- ``common``   — per-100g normalization + idempotent UPSERT keyed on
  ``(source, external_id)``.
- ``usda``     — FoodData Central CSV ingest (Foundation, SR Legacy, Branded).
- ``off``      — Open Food Facts nightly JSONL dump ingest.

Each module exposes a ``download_*`` function (the only network/disk-heavy step)
kept separate so it is never exercised by the test suite; tests drive the parse
and UPSERT paths with small inline fixtures instead.
"""
