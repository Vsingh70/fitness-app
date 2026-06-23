# Programs iOS Port — Phase 1 (model + screen reshape)

> Ports the now-settled web Programs shape into `apps/ios/GymApp/Features/Programs`. Built by
> the loop: Builder = `ios-dev`, Checker = `qa-verifier` (gate = `xcodebuild ... build` succeeds;
> there are no iOS tests). Visual-verified via simulator screenshots.

**Context (from the iOS map):** iOS Programs is a polished but **100% mock-only** prototype —
`Core/MockData.swift` structs bake in the OLD model (`daysPerWeek`, `weeks`, `currentWeek`,
`deloadWeek`), and the 9 views read it. No API client, no auth, no Codable, no persistence. The
`Core/Design` components (Buttons, Cards, MiniSegmented, UnderlineSegmented, ScreenHeader,
StatTile, GroupedRow, Chips, Rings) are reusable and stay. Routing exists (Programs nested under
the Workouts tab via a `Route` enum + `programNavigate`/`programPopToOverview` env closures).

**Phase 1 scope (this plan):** reshape the iOS models + all Programs screens to the new
microcycle/mesocycle model, keeping the mock-data architecture, so iOS reaches information +
visual parity with the shipped web redesign. **Phase 2 (separate, bigger):** build a networking +
keychain-auth + Codable API layer and wire `ProgramsStore` to the live backend — flagged for a
decision, not in this plan.

**Build gate (Checker):**
`xcodebuild -project apps/ios/GymApp.xcodeproj -scheme GymApp -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -quiet CODE_SIGNING_ALLOWED=NO build` → `** BUILD SUCCEEDED **`.

## Build order (rebind-first, so each task compiles)

### Task A — reshape models + make everything compile on the new shape

**Files:** `Core/MockData.swift` (models + sample data) and every view that reads the changed
fields (`ProgramsStore`, `ProgramsHomeView`, `ProgramEditorView`, `ProgramDayView`,
`MesocycleBarView`, `TemplatesBrowseView`, `TemplateDetailView`, `ProgramsOnboardingView`,
`CalendarView`).

Model changes (mirror the API/`ProgramResponse` shape):
- `ProgramDay` → a **slot**: add `isRestDay: Bool`; keep `name`, `exercises`. (Optionally rename to
  `ProgramSlot`; if so, update refs. A rename is optional — adding `isRestDay` + `slotIndex` is the
  minimum.) Add `slotIndex: Int`.
- `Program`: drop `daysPerWeek`/`weeks`/`currentWeek`/`deloadWeek`; add
  `microcycleLength: Int` (= slot count), `mesocycleLengthMicrocycles: Int`, and a rotation
  position (`currentSlotIndex`, `currentRepetition`, `inDeload`) — mock these.
- `ProgramTemplate`: drop `daysPerWeek`/`weeks`; add `microcycleLength`,
  `mesocycleLengthMicrocycles`, and `visibility` (curated/private/shared) + `ownerIsMe: Bool` for
  the browse grouping.
- Update `MockData` sample programs/templates to the new shape, with explicit rest slots (so a
  cycle reads e.g. Push/Pull/Legs/Rest/Upper/Lower/Rest).

Then update every view mechanically so the project **compiles** (display microcycle length instead
of days_per_week, slot index instead of week, etc.). No redesign yet beyond what's needed to build.
- **DoD:** `xcodebuild ... build` = BUILD SUCCEEDED.

### Task B — screen parity with the web redesign

Match the shipped web shape (`tasks/redesign/02-programs-screens.md`), reusing `Core/Design`:
- `MesocycleBarView`: weeks → **microcycle repetitions** (done/current/future) + a trailing
  **deload** cell when auto-deload; label "Cycle 2 of 4" from `mesocycleLengthMicrocycles`.
- `ProgramsOnboardingView`: the two-card chooser ("Follow a template" / "Build your own") is the
  entry for **every** create, not first-run only (reachable from a "New program" action too).
- `ProgramsHomeView` (spine): masthead meta "8-slot cycle, 5 training"; today = current rotation
  slot (rest slot → quiet "Rest day" + next training slot); "This microcycle" list with rest slots
  italic/muted; library rows with **Activate / Deactivate** and an overflow with **Duplicate** and
  **Save as template** (name + visibility); a "Create a new program" → chooser.
- `ProgramEditorView`: a **slot rail** with a per-slot **Rest** toggle and "+ Add slot" (live
  "N-slot microcycle"); a **Mesocycle length** control (microcycles, deload excluded) + auto-deload
  toggle when periodization is set; rest slot hides the exercise list. Use SwiftUI drag-reorder
  (`.onMove`) on the slot rail.
- `TemplatesBrowseView`: group into **Curated / My templates / Shared**; meta = microcycle +
  mesocycle length.
- `ProgramDayView` (slot detail): rest slots show the rest state; training slots show
  Sets/Reps/intensity/Rest + Start.
- **DoD:** `xcodebuild ... build` = BUILD SUCCEEDED.

## Visual verification (orchestrator, not the loop)
Boot the iPhone 17 Pro simulator, install + launch the built app, screenshot the spine, builder,
browse, and chooser (light + dark via simulator appearance), `xcrun simctl io booted screenshot`.

## Out of scope (Phase 2, needs a decision)
- Networking client + keychain/bearer auth + Codable models + wiring `ProgramsStore` to the live
  API (`GET /programs`, `/position`, `/advance`, slot CRUD, duplicate, save-as-template). This is an
  app-wide data-layer decision, not Programs-specific.
- A first-class Programs tab (currently nested under Workouts) — keep as-is unless decided otherwise.
