# Food data refresh (USDA FDC + Open Food Facts)

The app self-hosts its food catalogue: it bulk-ingests **USDA FoodData Central**
(Foundation, SR Legacy, Branded) and the **Open Food Facts** nightly dump into
the `foods` table, then searches/resolves barcodes locally (no paid provider, no
rate limits, works offline once ingested). Spec: `tasks/redesign/07-nutrition.md`.

This runbook covers the scheduled refresh that keeps both datasets current.

- **USDA**: refresh **monthly** (FDC publishes new releases roughly monthly).
- **Open Food Facts**: refresh **weekly or monthly** (a full dump is published
  nightly; we don't need every night).

All commands run on the VPS from the API app dir, e.g.:

```
ssh ops@<host>
cd /srv/gym-app/apps/api          # adjust to the deploy path
```

The ingest scripts are idempotent — they UPSERT on `(source, external_id)`, so a
re-run refreshes rows in place rather than duplicating them. Safe to re-run.

## Disk budget (estimate before the first OFF import)

| Dataset | Download | Notes |
| --- | --- | --- |
| USDA Foundation + SR Legacy | ~50–100 MB zipped | Few thousand clean generic foods. |
| USDA Branded | ~1–2 GB zipped CSV | US branded with GTIN/UPC. Optional. |
| Open Food Facts dump | ~9 GB gzipped JSONL | ~3–4M products; we keep only the lean fields. |

Postgres footprint after ingest is far smaller than the OFF download because we
drop everything except name, brand, serving, per-100g macros, and barcode, and
skip products with no usable barcode/macros. Budget **~10–15 GB free** on the
data volume for the OFF download + extract before the first import, and run it
off-hours. Delete the downloaded dump after a successful ingest.

## USDA FoodData Central (monthly)

FDC bulk bundles: https://fdc.nal.usda.gov/download-datasets.html

The download step is a function (`download_fdc_bundle`) kept separate from the
ingest so it never runs in CI/tests. The runner reads CSVs already extracted to
`USDA_DATA_DIR` (default `apps/api/seed/usda/`).

```
# 1) Download + extract the bundles you want into the seed dir.
#    (Foundation + SR Legacy are the quality core; Branded is optional/large.)
uv run python - <<'PY'
from pathlib import Path
from scripts.ingest.usda import download_fdc_bundle, DEFAULT_DATA_DIR
for bundle in ("foundation", "sr_legacy", "branded"):   # drop "branded" to skip it
    download_fdc_bundle(bundle, DEFAULT_DATA_DIR)
PY

# 2) Ingest. Reads food.csv, food_nutrient.csv, and (if present) branded_food.csv.
USDA_DATA_DIR=apps/api/seed/usda uv run python -m scripts.ingest.usda
```

Notes:
- FDC `food_nutrient.csv` amounts are already per-100 g for these data types, so
  ingest is a straight column map — no serving math.
- `data_type` is written to `foods.payload.category`; search ranks
  `foundation_food` / `sr_legacy_food` above `branded_food`.
- Branded rows with a GTIN also get a second row keyed by the barcode, so a scan
  of a USDA-branded product resolves to clean USDA data before OFF.

## Open Food Facts (weekly or monthly)

Dump: https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz

```
# 1) Download the nightly dump (~9 GB). Heavy; off-hours.
uv run python - <<'PY'
from scripts.ingest.off import download_off_dump, DEFAULT_DUMP_PATH
download_off_dump(DEFAULT_DUMP_PATH)
PY

# 2) Stream-ingest it (line-by-line; memory stays flat).
OFF_DUMP_PATH=apps/api/seed/off/openfoodfacts-products.jsonl.gz \
  uv run python -m scripts.ingest.off

# 3) Reclaim disk: delete the dump once the ingest reports rows_written.
rm apps/api/seed/off/openfoodfacts-products.jsonl.gz
```

The ingest skips products with no barcode, no name, or no usable per-100g macro,
so the OFF long tail of empty crowd-sourced entries never lands in `foods`.

## Scheduling (cron on the VPS)

Add to the deploy user's crontab (`crontab -e`). Adjust the app path.

```
# USDA: 04:30 on the 1st of each month.
30 4 1 * *  cd /srv/gym-app/apps/api && \
  uv run python - <<'PY' && \
  USDA_DATA_DIR=apps/api/seed/usda uv run python -m scripts.ingest.usda
from pathlib import Path
from scripts.ingest.usda import download_fdc_bundle, DEFAULT_DATA_DIR
for b in ("foundation", "sr_legacy"):
    download_fdc_bundle(b, DEFAULT_DATA_DIR)
PY

# Open Food Facts: 03:00 every Sunday.
0 3 * * 0  cd /srv/gym-app/apps/api && \
  uv run python - <<'PY' && \
  OFF_DUMP_PATH=apps/api/seed/off/openfoodfacts-products.jsonl.gz uv run python -m scripts.ingest.off && \
  rm -f apps/api/seed/off/openfoodfacts-products.jsonl.gz
from scripts.ingest.off import download_off_dump, DEFAULT_DUMP_PATH
download_off_dump(DEFAULT_DUMP_PATH)
PY
```

(For a real schedule, wrap each in a small shell script and log to
`/var/log/gym-food-ingest-*.log` rather than inlining heredocs in crontab.)

## Verify after a refresh

```
# Row counts per source.
psql "$DATABASE_URL" -c \
  "SELECT source, count(*) FROM foods GROUP BY source ORDER BY source;"

# A live search smoke test (replace TOKEN).
curl -sH "Authorization: Bearer TOKEN" \
  "https://<host>/v1/foods/search?q=chicken%20breast" | jq '.items[0]'
```

USDA generic foods should rank first for clean queries; OFF fills branded/barcode
breadth. A barcode miss falls back to a live OFF lookup that caches the result
into `foods` for next time.

## Troubleshooting

- **Ingest finds no CSVs / dump** (`usda_csvs_missing`, `off_dump_missing` in
  logs): the download step didn't run or wrote elsewhere. Check `USDA_DATA_DIR` /
  `OFF_DUMP_PATH` match where the download wrote.
- **Disk full during OFF import**: the download (~9 GB) plus working space ran the
  volume out. Delete the previous dump first, or download to a larger volume and
  point `OFF_DUMP_PATH` at it.
- **A row's macro looks absurd**: OFF is crowd-sourced; the ingest clamps macros
  to the column range and drops negatives, but bad source values still slip
  through. De-duplication and source ranking keep them out of the way of clean
  USDA hits; report egregious cases upstream to OFF.
- **Search feels stale**: confirm the cron ran (check the logs) and re-run the
  ingest manually; it's idempotent.
```
