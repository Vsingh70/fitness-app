# Nutrition food data: free, self-hosted, deep

Replaces the FatSecret integration with a free food-data stack that the app owns.
This is the substantive nutrition change in the redesign; the page layout stays the
Direction-A log-first shape (`04-page-specs.md`). Hard requirement: the data must be
free. Both sources below are free.

## 1. Why the change

FatSecret was the planned food source but never went live (credentials and IP
allowlist pending), and its free tier does not return deep enough results to make a
search-first page usable. Rather than rent a thin slice of a hosted database, the app
owns its food data by ingesting two free, large datasets into the existing `foods`
table and searching them locally.

Note: FatSecret is not actually a small database; the limitation is the free access
tier and regional bias, not raw size. Owning the data sidesteps both.

## 2. Sources (both free)

- **USDA FoodData Central (FDC)** — free with a data.gov API key, and published as bulk
  downloads. Use Foundation Foods and SR Legacy (high-quality generic/whole foods) plus
  the Global Branded Foods Database (US branded, GTIN/UPC). This is the quality core for
  generic foods.
- **Open Food Facts (OFF)** — free, open data, roughly 3 to 4 million products from
  150+ countries, the best global barcode/branded coverage. Published as nightly full
  database dumps. Crowd-sourced, so quality is uneven; treat as breadth, not authority.

Together these exceed FatSecret's free-tier coverage at zero cost. No paid provider
(Nutritionix, Edamam) is used; both were priced out for a personal app.

Restaurant and menu items are intentionally out of scope: free sources are weak there
and the maintainer confirmed grocery and whole-food coverage is enough. Eating out is
logged by closest match or manual entry.

## 3. Architecture: self-host bulk ingest

Decision: ingest the bulk datasets into Postgres and search locally. The app's
existing `foods` table already has `source` (`usda`, `off`, `custom`, `user`),
`external_id`, per-100g macros, and a `pg_trgm` GIN index on `name`. This stays the
source of truth.

- **Ingestion pipeline** (a script under `scripts/`, runnable on the VPS):
  - USDA: download the FDC bulk files (Foundation, SR Legacy, Branded), normalize to
    per-100g macros (`kcal`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`), upsert into
    `foods` with `source = usda` and `external_id = FDC id`.
  - OFF: download the nightly dump, filter to products with usable nutrition per 100g,
    upsert with `source = off` and `external_id = barcode`.
  - Idempotent upserts keyed on `(source, external_id)` so re-runs refresh rather than
    duplicate.
- **Search**: the existing `pg_trgm` fuzzy search over `foods.name` serves the quick-add
  bar. Rank USDA Foundation/SR Legacy above branded and OFF so clean generic foods
  surface first; de-duplicate near-identical names. Instant, no rate limits, works
  offline once ingested.
- **Barcode**: scan resolves against local `foods` by `external_id`; a miss falls back
  to a live OFF lookup and caches the result into `foods`.
- **Refresh**: a scheduled job (monthly for USDA, weekly or monthly for OFF) re-runs the
  ingest to pick up new and corrected entries. Document it as a runbook alongside the
  existing `docs/runbooks/`.

Storage: the OFF dump is large; ingest only fields the app uses (name, brand, serving,
per-100g macros, barcode) and drop the rest to keep the table lean. Estimate and
document disk needs before the first full OFF import.

## 4. Code changes

- Remove the FatSecret client and its config and secrets. Update CURRENT-STATE and
  `00-overview/data-model.md` (the `foods.source` enum already fits; no enum change).
- Add the ingestion script(s) and a thin search service over `foods` (replacing the
  FatSecret search path the UI calls).
- The nutrition UI (`quick-add-bar.tsx`, `add-meal-sheet.tsx`, `barcode-scanner.tsx`,
  `ingredient-picker.tsx`) keeps its shape; only the data source behind search and
  barcode changes.

## 5. Tradeoffs and risks

- OFF data quality is uneven; ranking and de-duplication matter so junk entries do not
  bury good ones. Prefer USDA for generic foods.
- First OFF import is heavy (download size and ingest time); run it off-hours on the VPS.
- US-centric generic data (USDA) plus global branded (OFF) leaves some non-US generic
  gaps; acceptable for this user base. Custom and user food entries (already supported)
  fill the rest.

## 6. Acceptance

- [ ] FatSecret client, config, and secrets removed.
- [ ] USDA FDC bulk data ingested into `foods` with normalized per-100g macros.
- [ ] Open Food Facts dump ingested for barcode and global branded coverage.
- [ ] Quick-add search returns deep results from local `foods` via pg_trgm, ranked with
      USDA generic foods first, offline-capable.
- [ ] Barcode scan resolves locally with a live OFF fallback that caches.
- [ ] A documented refresh job keeps both datasets current.
- [ ] No paid food-data dependency anywhere in the stack.

## 7. Out of scope

- Restaurant/menu item coverage (free sources are weak; logged manually).
- Photo meal recognition (dropped earlier, stays dropped).
- Recipe/ingredient NLP parsing.
