# 08.03 iOS programming and scheduling

## Context

iOS equivalent of `03.02 program builder` and `03.03 scheduling`.

## Goal

Browse templates, copy them, edit programs, and see the calendar of scheduled workouts.

## Screens

### Programs tab root (`Features/Programs/ProgramsHomeView.swift`)
- Segmented control: Mine / Templates.
- Mine: list of user programs with active one pinned and a Use/Activate state.
- Templates: grid of cards with goal, days/week, weeks. Tap to preview.

### Template detail
- Read-only preview week by week.
- Primary button "Use this program" copies it.

### Program editor (`Features/Programs/ProgramEditorView.swift`)
- Header with metadata (editable fields).
- Tabs for weeks, segmented control or paged TabView for days within the week.
- Day editor:
  - Drag-to-reorder exercises.
  - Tap exercise to edit targets (sets/reps/RPE/rest/progression strategy).
  - Swipe to remove.
- "Activate" sheet asking start date and starting weekday.
- Per-muscle volume warnings via a collapsible bottom inspector.

### Calendar (`Features/Programs/CalendarView.swift`)
- Native iOS 17 `CalendarView` or a custom SwiftUI grid for finer control.
- Each day shows up to 2 workout chips with overflow indicator.
- Tap day -> scheduled workout sheet with start button.
- Long-press a chip -> reschedule via DatePicker. Sheet asks "Shift remaining program?" toggle.

## Deliverables

1. All views with `@Observable` view models.
2. Drag-and-drop reordering inside the program editor.
3. Activation flow with date and weekday picker.
4. Calendar view + reschedule sheet.
5. UI tests for: copy template, edit a day, activate.

## Acceptance criteria

- Visual parity with the web implementation in the design system.
- Editing exercises in a program day saves on background, with optimistic UI.
- Calendar performance: scrolling stays at 60fps over 6 months of data.

## Dependencies

- `08.01 iOS app skeleton`
- `03.01`, `03.02`, `03.03`

## Out of scope

- Sharing programs (no social layer).
