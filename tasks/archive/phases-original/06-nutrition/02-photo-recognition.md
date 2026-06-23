# 06.02 AI meal photo recognition (DROPPED)

## Status

Dropped. This feature was specced but never built, and we have decided not to build it. Nutrition food entry is handled by manual entry, the FatSecret search API, and barcode scanning (see `06.04`, `06.05`, `06.06`). The only leftover artifact, the unused `meals.photo_url` column, was removed.

## Why

- It was never implemented: there is no recognize endpoint, no Ollama vision client, and no upload pipeline.
- The three concrete entry paths (manual, database search, barcode) cover real use without the cost and accuracy problems of plate photo estimation.
- Keeps the Ollama VPS focused on text models for rationales and analytics.

## What this means

- No `POST /v1/meals/recognize`, no LLaVA model, no meal photo storage.
- `meals.photo_url` removed (migration in the photo-recognition removal change).
- The nutrition "Add food" surface has Search, Scan, and Manual only. No Photo tab.

## See instead

- `06.01 Food database, barcode, and search`
- `06.04 Nutrition database API (FatSecret)`
- `06.05 Meal planning`
- `06.06 Meal plan logging and flexible tracking`
