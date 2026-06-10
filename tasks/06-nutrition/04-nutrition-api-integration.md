# 06.04 Nutrition database API (FatSecret)

## Context

`06.01 Food database` planned a USDA bulk seed plus Open Food Facts for barcodes. We are replacing the primary search source with a live nutrition API so users get a large, maintained catalog with real serving options (g, cups, oz, pieces) without us hosting and updating a giant dataset. Preferred provider: the FatSecret Platform API. It covers both text search and barcode lookup, and it returns named servings with gram weights, which is exactly what meal entry needs.

This task is the foundation the meal planning and logging tasks build on. It supersedes the USDA seed approach in `06.01`; custom user foods and the `foods` cache table stay.

Reference: `06-nutrition/01-food-database.md`, `00-overview/data-model.md` (foods), `00-overview/api-conventions.md`.

## Goal

A server-side FatSecret client behind our existing food endpoints, so search, barcode lookup, and food detail all resolve through FatSecret, get normalized into our `foods` schema, and get cached. The client and credentials follow the same encrypted-secret and vault patterns used by the Google Health integration.

## FatSecret integration notes

- Auth: OAuth 2.0 client credentials (server to server). Store client id and secret in vault, mirror the Google Health secret handling.
- IP allowlist: the basic tier requires whitelisting our server egress IP. Document this. The API VPS IP is in the deployment runbook.
- Methods to wrap:
  - `foods.search` (v3) for text search with paging.
  - `food.get` (v4) for full detail including the servings list.
  - `food.find_id_for_barcode` then `food.get` for barcode scans (GTIN-13; pad UPC-A to 13).
- Rate limits and errors: wrap with retries and map provider errors to our standard error shape. Cache aggressively to stay under quota.

## Data model

- Extend the `foods.source` enum to include `fatsecret`. `external_id` holds the FatSecret food id.
- Servings: FatSecret returns multiple servings per food, each with a description and a metric gram weight. Persist them so the UI can offer "1 cup", "1 serving", "100 g". Add a `food_servings` table: `id`, `food_id`, `description`, `metric_amount`, `metric_unit` (g or ml), `grams` (resolved gram weight), `is_default`. Keep the per-100g macro columns on `foods` as the canonical math base.
- A migration for the enum value and the `food_servings` table.

## Endpoints

Keep the existing public shapes from `06.01` so callers do not change:

- `GET /v1/foods/search?q=...` now resolves misses through FatSecret, caches into `foods` plus `food_servings`, returns our normalized rows including their servings.
- `GET /v1/foods/barcode/{barcode}` does the FatSecret barcode dance, caches, returns the food with servings. If FatSecret has no match, keep the Open Food Facts fallback from `06.01`, then 404 with `code = 'not_found'` so the client can offer custom entry.
- `GET /v1/foods/{id}` returns the food plus its servings.
- Custom food CRUD from `06.01` is unchanged.

## Deliverables

1. FatSecret client wrapper (`apps/api/app/clients/fatsecret.py`) with OAuth 2.0 client credentials, retries, and response mapping to our schema including servings.
2. Config and vault entries for the client id and secret; reuse the existing secret patterns.
3. Migration: `fatsecret` source enum value plus the `food_servings` table.
4. Search, barcode, and detail endpoints resolving and caching through FatSecret, OFF kept only as a barcode fallback.
5. Tests: search miss calls FatSecret (mocked) and caches; cached hit does not call out; barcode maps a known GTIN to a food with servings; servings normalize to correct gram weights.

## Acceptance criteria

- A search for "chicken breast" returns FatSecret results with at least one gram-based serving in the top few, cached on first call.
- A real barcode resolves to a food with named servings in under 2 seconds first time and under 200 ms cached.
- Every returned food exposes at least one serving with a resolved gram weight, so downstream meal entry can convert servings to grams.

## Dependencies

- `01.02 FastAPI skeleton`
- `06.01 Food database, barcode, and search` (custom foods, cache table, OFF fallback)

## Out of scope

- The USDA bulk seed (dropped in favor of the live API; existing seeded rows can stay).
- Meal entry UI and meal plans (tasks `06.05` and `06.06`).
- Photo recognition.
