# 06.01 Food database, barcode, and search

## Context

Three food entry paths: barcode scan (Open Food Facts), search (USDA FoodData Central), and custom entries. Photo recognition is a separate task.

Reference: `00-overview/data-model.md` (foods).

## Goal

A unified foods table seeded with USDA, lookups via OFF barcodes, fuzzy search across both, and custom user food creation.

## USDA seed

- Use FoodData Central's "Foundation" + "SR Legacy" + a subset of Branded Foods. Avoid loading the full branded set (millions of rows); we'll query OFF live for barcodes instead.
- Download CSVs, transform to our schema, bulk-load.
- Store `source = 'usda'`, `external_id = FDC ID`.
- Normalize all nutrient values to per-100g.

## Open Food Facts lookup

When a barcode is scanned:
1. Check our DB first by `(source='off', external_id=barcode)`.
2. If miss, call `https://world.openfoodfacts.org/api/v2/product/{barcode}.json`.
3. Parse the response into our schema. Cache the result by inserting into `foods`.
4. If OFF doesn't have it, return 404 with `code = 'not_found'` and the client can prompt the user to add a custom food.

## Search

- pg_trgm on `foods.name`.
- Query: `q`, `source` filter, optional `min_protein_per_100g`.
- Rank: prefer custom + USDA Foundation entries over branded. Then trigram similarity.
- Cursor paginated.

## Endpoints

- `GET /v1/foods/search?q=chicken%20breast`
- `GET /v1/foods/barcode/{barcode}` — does the OFF dance described above.
- `POST /v1/foods` create a custom food. `source = 'custom'`, `owner_id = current user`.
- `PATCH /v1/foods/{id}` only for owner.
- `DELETE /v1/foods/{id}` only for owner; archive (`archived_at`) if referenced by any `meal_items`.

## Web UI

- Settings: a "Foods" page where users see their custom entries and recently used items, can edit them.
- Food picker sheet shared by meal logging.

## Deliverables

1. Migration for `foods` (with archived_at).
2. USDA download + transform script in `apps/api/scripts/seed_foods.py`. Document the manual data download step (USDA requires accepting their terms).
3. OFF client wrapper with retries and a sensible User-Agent.
4. Search endpoint + barcode endpoint + custom CRUD.
5. Tests covering: barcode hit cached, barcode miss falls through to OFF (mocked), search ranking.

## Acceptance criteria

- After seed, a search for "chicken breast" returns relevant USDA items in the top 5.
- A real barcode scan (test with a known UPC) returns nutrition data in under 2 seconds first time, under 200ms cached.
- Custom food creation works end-to-end.

## Dependencies

- `01.02 FastAPI skeleton`

## Out of scope

- Photo recognition (next task).
- Meal logging UI (task 06.03).
