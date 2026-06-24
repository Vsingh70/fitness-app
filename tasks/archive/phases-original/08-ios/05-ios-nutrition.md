# 08.05 iOS nutrition

## Context

iOS equivalent of `06.x nutrition`. Native barcode scanner via AVFoundation, native camera capture for photo recognition.

## Goal

Full meal logging on iOS, including barcode and photo flows.

## Screens

### Nutrition home (`Features/Nutrition/NutritionHomeView.swift`)
- Top: kcal ring + 3 macro rings (protein/carbs/fat).
- Meal sections (Breakfast/Lunch/Dinner/Snacks).
- FAB "+ Add food" -> sheet with three tabs (Search, Scan, Photo).

### Search tab
- `UISearchBar`-style search.
- Recent + favorites pinned.

### Scan tab (`Features/Nutrition/BarcodeScannerView.swift`)
- AVFoundation VNBarcodeObservation for EAN/UPC.
- On detect, hit `GET /v1/foods/barcode/{barcode}`.
- Show food preview sheet with grams input slider; tap Add.

### Photo tab (`Features/Nutrition/PhotoRecognitionFlow.swift`)
- Capture or pick a photo.
- POST to `/v1/meals/recognize`.
- Show candidates with confidence; user adjusts grams and confirms.

### History
- Daily totals over time.
- Adherence calendar.

### Plans
- List + edit + activate.

## Native niceties

- Use the system camera for both barcode and photo (consistent UX).
- HealthKit integration to write energy/protein/carbs/fat to Health (opt-in setting).

## Deliverables

1. All views.
2. Barcode scanner module with proper lifecycle (release the AV session on background).
3. Photo flow with upload progress.
4. HealthKit write (opt-in).
5. UI tests for the three add paths.

## Acceptance criteria

- Barcode scan to logged meal in 3 taps and under 4 seconds end-to-end.
- Photo flow accepts a 10MB photo, shows progress, and lists candidates.
- HealthKit writes appear in the Health app when enabled.

## Dependencies

- `08.01 iOS app skeleton`
- `06.01`, `06.02`, `06.03`

## Out of scope

- Apple Watch standalone food logging.
