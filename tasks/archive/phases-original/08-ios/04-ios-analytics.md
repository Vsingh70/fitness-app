# 08.04 iOS analytics and insights

## Context

iOS equivalent of `05.x analytics`. Swift Charts.

## Goal

Insights tab with prioritized cards, volume charts, exercise drill-down.

## Screens

### Insights home (`Features/Insights/InsightsHomeView.swift`)
- Prioritized list of insight cards (action > warn > info).
- Each card: subject, severity icon, one-sentence rationale, primary action (e.g. "Adjust program"), dismiss via swipe.
- Section: "Volume this week" - stacked bar of per-muscle working sets vs target ranges.
- Section: "Recent PRs".

### Volume detail (`Features/Insights/VolumeDetailView.swift`)
- Time series per muscle using Swift Charts.
- Toggle between sets and tonnage.
- Per-muscle drill-down with exercise breakdown for the selected window.

### Exercise analytics (`Features/Insights/ExerciseAnalyticsView.swift`)
- Triggered from history view or insight deep links.
- e1RM, volume, average RPE charts.
- Sets scatter.
- Variant suggestions list.

## Native niceties

- Swift Charts interactivity: pinch to zoom on time series, tap to scrub.
- Share sheet: export an exercise chart as an image (used for any future social sharing the user might want, even without an in-app social layer).

## Deliverables

1. All views and view models.
2. Charts with proper accessibility labels.
3. Insight deep links into the program editor and exercise detail.
4. Snapshot tests for chart variants.

## Acceptance criteria

- Insights load under 600ms with a year of data.
- Exporting a chart produces a clean 1080x1080 PNG with our branding.
- VoiceOver reads all charts as data summaries.

## Dependencies

- `08.01 iOS app skeleton`
- `05.01`, `05.02`, `05.03`

## Out of scope

- Apple Health export (later).
