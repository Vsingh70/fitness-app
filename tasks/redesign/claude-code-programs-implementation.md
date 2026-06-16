# Programs — full implementation manifest (Claude Code)

Build the **entire Programs feature**: first-run onboarding, Direction A active
overview (+ multi-program library), and every supporting screen. This is the
**file-by-file checklist**; the *behavioral spec* lives in
`claude-code-programs-A.md` and the *visual truth* in `programs/index.html`
(+ `programs/screens.jsx`, `programs/programs.css`). Read those alongside this.

Prereq: the editorial systems (`claude-code-editorial-handoff.md` web,
`claude-code-editorial-ios.md` iOS) are already in place — tokens, serif type,
hairlines, clay accent, `Card`-less surfaces.

Legend: ☐ create · ✎ edit existing · ↺ reuse as-is.

---

## A. WEB — `apps/web`

### A1. Data / API layer
- ✎ ☐ `src/lib/types/program.ts` — add/confirm:
  ```ts
  export type IntensityMode = "rpe" | "rir" | "off";
  export type RepMode = "range" | "target";
  export interface ProgramExercise { id; name; muscle; sets: number; repMode: RepMode; reps: string; intensityTarget: string; rest: string; progressionNote?: string; }
  export interface ProgramDay { id; name; exercises: ProgramExercise[]; }
  export interface Program { id; name; goal; progressionStrategy; weeks: number; deloadWeek?: number; currentWeek: number; intensityMode: IntensityMode; status: "active"|"inactive"|"archived"; days: ProgramDay[]; }
  ```
- ☐ `src/lib/api/programs.ts` — `listPrograms()`, `getProgram(id)`,
  `createProgram()`, `activateProgram(id)`, `deleteProgram(id)`,
  `useTemplate(templateId)`, `listTemplates(category?)`, `getTemplate(id)`.
  (Wire to existing endpoints; stub `create`/`useTemplate` to return a draft if
  the backend isn't ready.)
- ☐ `src/lib/hooks/use-programs.ts` — React Query wrappers for the above +
  optimistic `activate`/`delete`.

### A2. Routing (App Router)
- ✎ ☐ `src/app/(app)/programs/page.tsx` — **gate**: `listPrograms()` empty →
  `<ProgramsOnboarding/>`, else `<ActiveProgramView/>`.
- ☐ `src/app/(app)/programs/templates/page.tsx` — `<BrowseTemplates/>`.
- ☐ `src/app/(app)/programs/templates/[id]/page.tsx` — `<TemplateDetail/>`.
- ☐ `src/app/(app)/programs/[id]/page.tsx` — `<ActiveProgramView programId/>` (view any program).
- ☐ `src/app/(app)/programs/[id]/days/[dayId]/page.tsx` — `<PerDayDetail/>`.
- ☐ `src/app/(app)/programs/[id]/edit/page.tsx` — `<ProgramBuilder/>`.
- ☐ `src/app/(app)/programs/new/page.tsx` — `<ProgramBuilder draft/>`.

### A3. Components — `src/components/programs/`
- ☐ `onboarding.tsx` → `ProgramsOnboarding` — two `.ow-card` choices (template→`/programs/templates`, build→`/programs/new`). See `WebOnboard`.
- ☐ `mesocycle-bar.tsx` → `MesocycleBar({weeks,currentWeek,deloadWeek})` — `.meso` cells. Reused by overview.
- ☐ `active-program.tsx` → `ActiveProgramView` — composes the four blocks below. See `WebDirA`.
  - ☐ `program-masthead.tsx` → `ProgramMasthead` (`.aw-mast` + `MesocycleBar`).
  - ☐ `today-card.tsx` → `TodayCard` (`.aw-today` + Start).
  - ☐ `week-list.tsx` → `WeekList` (`.aw-week` rows, status states).
  - ☐ `program-library.tsx` → `ProgramLibrary` (`.aw-progs`) — rows with Active/Activate/Restore + **trash→confirm→delete**, "+ Create a new program". Uses `useTheme` confirm dialog.
- ☐ `browse-templates.tsx` → `BrowseTemplates` — `.tw-filters` + `.tw-gallery`. See `WebTemplates`.
- ☐ `template-detail.tsx` → `TemplateDetail` — `.dw-*` hero/specs/day breakdown + "Use this template"→`useTemplate`. See `WebDetail`.
- ☐ `per-day-detail.tsx` → `PerDayDetail` — `.xw-*` scheme rows + progression + Start. See `WebPerDay`.
- ☐ `program-builder.tsx` → `ProgramBuilder` — `.ew-grid`; left day-rail (dnd-kit) + **Details panel incl. global `IntensityModeControl`**; right `ExerciseEditorRow[]`. See `WebBuilder`.
  - ☐ `exercise-editor-row.tsx` → `ExerciseEditorRow` (`.ew-ex`) — Sets field, **`RepModeToggle` (Range/Target)**, and intensity-target field shown only when `program.intensityMode !== "off"` (label from mode).
  - ☐ `mini-segmented.tsx` → `MiniSegmented({options,value,onChange})` — `.mini-seg` ink-active control. Reused for repMode + intensityMode.
  - ☐ `intensity-mode-control.tsx` → `IntensityModeControl` — `MiniSegmented` RPE/RIR/Off bound to `program.intensityMode`, caption "Applies to every exercise."

### A4. Nav
- ✎ `src/components/layout/sidebar.tsx` — ensure Programs entry routes to `/programs`.

---

## B. iOS — `apps/ios`

### B1. Models — `Sources/Models/`
- ✎ ☐ `Program.swift` — `IntensityMode`, `RepMode` enums; `ProgramExercise`,
  `ProgramDay`, `Program` (with `intensityMode`, per-exercise `repMode`).
- ☐ `ProgramsStore.swift` — `@Observable`: `programs`, `activeProgram`,
  `templates`; `activate`, `delete`, `create`, `useTemplate`.

### B2. Views — `Sources/Features/Programs/`
- ☐ `ProgramsRootView.swift` — switch: `store.programs.isEmpty ? ProgramsOnboardingView : ActiveProgramView`.
- ☐ `ProgramsOnboardingView.swift` — two `.pi-ecard`-style choice cards. See `IosOnboard`.
- ☐ `MesocycleBarView.swift` — `.pi-meso` cells.
- ☐ `ActiveProgramView.swift` — masthead + `MesocycleBarView` + today card + week list + **library**. See `IosDirA`.
  - ☐ `ProgramLibrarySection.swift` — `List` rows with **`.swipeActions` → Delete (role: .destructive)**, Activate/Active trailing, "+ Create a new program" row.
- ☐ `BrowseTemplatesView.swift` — filter pills + template rows. See `IosTemplates`.
- ☐ `TemplateDetailView.swift` — hero/specs/days + pinned bottom **Use this template** bar. See `IosDetail`.
- ☐ `PerDayDetailView.swift` — scheme rows + progression + Start. See `IosPerDay`.
- ☐ `ProgramBuilderView.swift` — day rail + **global `IntensityModeControl` card** (`.pie-global`) + exercise blocks. See `IosBuilder`.
  - ☐ `ExerciseEditorBlock.swift` — Sets, `Range/Target` segmented + value, intensity target (hidden when `.off`), drag via `.onMove`.
  - ☐ `MiniSegmented.swift` — reusable compact segmented (ink-active).

### B3. Tab wiring
- ✎ `AppTabView.swift` — Programs tab → `ProgramsRootView`.

---

## C. Build order (recommended)
1. **Models/types + API/store** (A1, B1) — shape data, stub network.
2. **MiniSegmented + MesocycleBar** — shared primitives both platforms need.
3. **Onboarding** (gate + two cards) — smallest end-to-end slice.
4. **Active overview** (masthead → today → week → library) — the core screen.
5. **Multi-program** actions (activate / delete / create) wired to store.
6. **Builder** (day rail, Details + global intensity, exercise rows, rep/intensity controls).
7. **Templates → detail → "use template"** flow.
8. **Per-day detail**.
9. Polish: dnd persistence, confirm dialogs, light/dark pass, empty/loading/error.

## D. Definition of done (per screen)
Each screen passes when it (a) matches its frame in `programs/index.html` at the
target width, (b) uses only editorial tokens (no shadows/candy color, serif
titles+figures, hairlines, clay accent), (c) works in light **and** dark, and
(d) satisfies the acceptance checklist in `claude-code-programs-A.md §7`.

## E. The four global invariants (don't regress)
1. **First run** appears iff the user has **zero programs**.
2. **Multiple programs**: create / activate / delete all reachable from the overview.
3. **Reps** are per-exercise **Range or Target**.
4. **Intensity** is a **single program-wide** RPE / RIR / Off; per-exercise rows
   show only a target (and nothing when Off).

## F. Reference map
| Build target | Prototype component | CSS prefix |
|---|---|---|
| Onboarding | `WebOnboard` / `IosOnboard` | `.ow-` / `.pi-ecard` |
| Mesocycle bar | inline in `WebDirA`/`IosDirA` | `.meso` / `.pi-meso` |
| Active overview | `WebDirA` / `IosDirA` | `.aw-` / `.pia-` |
| Program library | in `WebDirA`/`IosDirA` | `.aw-prog*` / `.pia-prog*` |
| Browse templates | `WebTemplates` / `IosTemplates` | `.tw-` / `.pit-` |
| Template detail | `WebDetail` / `IosDetail` | `.dw-` / `.pid-` |
| Per-day detail | `WebPerDay` / `IosPerDay` | `.xw-` / `.pix-` |
| Builder | `WebBuilder` / `IosBuilder` | `.ew-` / `.pie-` |
| Mini segmented | `MiniSeg` | `.mini-seg` / `.ios-mini-seg` |

> Open `programs/index.html`, find the component named in the middle column, and
> read its exact markup/classes in `programs/screens.jsx`. The `.css` file is the
> single source for spacing, type, and color — port those values, don't reinvent.
