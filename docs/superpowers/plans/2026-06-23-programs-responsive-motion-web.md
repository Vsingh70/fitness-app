# Programs Web — Responsive + Motion Foundation and UI Redesign (Plans 2 & 3)

> **Plans 2 & 3 of the Programs vertical slice.** Depends on Plan 1 (backend, merged on
> `feat/programs-flexible-model`) and its regenerated `apps/web/src/lib/api/types.ts`.
> Built by the build-test-fix loop: Builder = `web-dev`, Checker = `qa-verifier`
> (`pnpm typecheck` / `pnpm lint` / `pnpm test` / `pnpm build`). UI quality is verified
> **visually** (run the app, screenshots) in addition to green checks.

**Goal:** Restore web typecheck against the new program model, then add a responsive +
motion foundation and redesign the Programs surface on it — fluid at every width, restrained
physical motion, editorial language unchanged.

**Architecture:** Build order is **rebind-first** so `pnpm typecheck` goes green early and
every later task is independently gateable: (1) rebind the 16 `programs/*` components to the
new types; (2) add the responsive/fluid token layer + install `motion`; (3) motion primitives;
(4) responsive layout shell; (5–9) redesign each Programs screen with the foundation + motion;
(10) polish + full green + visual verification.

**Tech Stack:** Next.js 15 (App Router), React 19, Tailwind v4 (CSS-first `@theme`),
TanStack Query, `motion` (motion/react), the editorial token system in
`src/styles/tokens.css` + `src/app/globals.css`.

---

## Design system additions (the part that needs design judgment — encode exactly)

### A. Responsive tokens (add to `src/app/globals.css` `@theme` and `tokens.css`)

Today there are no breakpoint or fluid tokens; the layout hard-switches sidebar↔tabbar at the
Tailwind default `md` (768) with nothing for tablet/mid-window. Add:

- **Breakpoints** (Tailwind v4 `@theme`): `--breakpoint-sm: 40rem; --breakpoint-md: 48rem;
  --breakpoint-lg: 64rem; --breakpoint-xl: 80rem; --breakpoint-2xl: 96rem;` (640/768/1024/1280/1536).
- **Fluid type scale** in `tokens.css` (`:root`), `clamp(min, fluid, max)`, then expose as
  `--text-*` Tailwind utilities in `@theme`. Bodies grow 15→17, headlines per the brief:
  - `--text-body: clamp(0.9375rem, 0.9rem + 0.35vw, 1.0625rem);`   /* 15 → 17 */
  - `--text-caption: clamp(0.75rem, 0.72rem + 0.15vw, 0.8125rem);`
  - `--text-h3: clamp(1.375rem, 1.2rem + 0.8vw, 1.75rem);`         /* 22 → 28 */
  - `--text-h2: clamp(1.75rem, 1.45rem + 1.3vw, 2.125rem);`        /* 28 → 34 */
  - `--text-h1: clamp(2.125rem, 1.7rem + 2vw, 2.75rem);`           /* 34 → 44 display */
  - Replace the hardcoded `body { font-size: 15px }` with `font-size: var(--text-body)`.
- **Fluid spacing rhythm** (`tokens.css`): a `--space-*` set used for page gutters and section
  rhythm so wide viewports breathe (fixes `02 §1`):
  - `--space-gutter: clamp(1rem, 0.5rem + 2.5vw, 2.5rem);`  /* page side padding */
  - `--space-section: clamp(1.5rem, 1rem + 2vw, 2.75rem);` /* vertical rhythm between blocks */
  - `--content-max: 72rem;`  /* fluid up to this, not a pinched fixed width */
- **Container helper**: a `.page-shell` utility (in `programs.css` or globals) =
  `width:100%; max-width:var(--content-max); margin-inline:auto; padding-inline:var(--space-gutter)`.
  Programs surfaces currently use `max-w-4xl/5xl/3xl` — replace with `.page-shell` so they go
  fluid with fluid gutters instead of fixed narrow.

### B. Motion system (`motion`, restrained + physical)

Install: `cd apps/web && pnpm add motion`. Import from `motion/react`. Wire to spring physics,
not the CSS-duration tokens (those stay for CSS transitions). Create
`src/lib/motion/` with:

- `springs.ts` — shared transitions:
  - `export const snappy = { type: "spring", stiffness: 460, damping: 38, mass: 0.9 } as const;`  /* ~150ms feel */
  - `export const soft   = { type: "spring", stiffness: 300, damping: 34 } as const;`
  - `export const sheet  = { type: "spring", stiffness: 380, damping: 40 } as const;`
- `use-reduced-motion-safe.ts` — wrap motion's `useReducedMotion()`; export a helper that
  returns variants collapsed to opacity-only (no transform/translate) when reduced motion is on.
- Primitives in `src/components/motion/`:
  - `<Reveal>` — entrance: `initial={{opacity:0, y:8}} animate={{opacity:1, y:0}}` with `soft`;
    collapses to opacity-only under reduced motion. Accepts `delay`.
  - `<RevealGroup>` — staggers children via `stagger(0.05)` (page-load reveal of a section;
    the one high-impact moment per surface, not scattered micro-anims).
  - `<Pressable>` — wraps a button/row: `whileHover` = subtle (border/elevation cue via a
    `data-hover` flag or `y:-1`, NOT a scale pop — editorial restraint), `whileTap={{scale:0.985}}`.
  - `<Sheet>` / `<Dialog>` content wrapped in `AnimatePresence` with `sheet` spring:
    enter `{opacity:0, y:12}`→`{opacity:1,y:0}`, exit reverse; backdrop fades.
- **Always** respect `prefers-reduced-motion`: every primitive checks the hook; under reduced
  motion, transforms are dropped and only opacity (or nothing) animates.

### C. Per-screen motion choreography (where motion goes — keep it sparse)

| Surface | Motion |
|---|---|
| Programs spine load | `RevealGroup` staggering masthead → cycle bar → today card → microcycle list |
| Builder slot rail | `Reorder.Group`/`Reorder.Item` (motion/react) drag-reorder with `layout` springs; new slot springs in via `AnimatePresence`; rest-toggle cross-fades the exercise panel |
| Cycle bar | cells animate `scaleX`/opacity fill on mount; current cell a quiet breathing opacity (reduced-motion: static) |
| Library rows | hover reveals the Deactivate/overflow affordance (opacity+x); activate state change animates `layout` |
| Dialogs (save-as-template, delete confirm) | `AnimatePresence` + `sheet` spring |
| Today card Start | `Pressable` tap; no idle motion |

Do **not** add scroll-jacking, parallax, or decorative loops — the editorial system is quiet.

---

## Tasks (loop order: rebind → foundation → screens → polish)

Each task: Builder implements, Checker runs the listed DoD. The Checker's full-green gate is
`pnpm typecheck && pnpm lint && pnpm test` (and `pnpm build` on the final task).

### Task 1 — Rebind the 16 `programs/*` components to the new types (restore typecheck)

**Files:** all of `src/components/programs/*` + `src/app/(app)/programs/**` (esp.
`new/page.tsx`), `src/lib/programs/types.ts`, `src/lib/hooks/programs.ts`,
`src/lib/api/programs.ts`.

Mechanical rebind to make `pnpm typecheck` green again — *no redesign yet*, just compile:
- Field renames everywhere they appear: `weeks`→(drop or `microcycle_length` where it was a
  count), `days_per_week`→`microcycle_length`, `day_index`→`slot_index`,
  `mesocycle_length_weeks`→`mesocycle_length_microcycles`. Add `is_rest_day` handling where days
  are rendered.
- `programs/new/page.tsx`: remove the hardcoded `weeks: 6, days_per_week: 4` from the create body
  (the new `ProgramCreate` has neither).
- `mesocycle-bar.tsx`/`useMesocycle`: the old `/mesocycle` endpoint is gone — switch the spine to
  `GET /programs/{id}/position` (`ProgramPositionResponse`). Add a `usePosition(id)` hook calling
  `getPosition` (mirror the removed `useMesocycle`); update `lib/api/programs.ts` to the new
  endpoints (slots, position, advance, duplicate, save-as-template) and drop removed ones.
- Update `lib/hooks/programs.ts` mutations: `addDay`→`addSlot`, `deleteDay`→`deleteSlot`, add
  `reorderSlots`, `toggleRest`, `duplicateProgram`, `saveAsTemplate`, `advancePosition`.
- **DoD:** `pnpm typecheck` GREEN, `pnpm lint` clean. (Web is restored even though the UI is not
  yet redesigned.) Commit: `fix(web): rebind programs UI to flexible microcycle model`.

### Task 2 — Responsive + fluid token layer

**Files:** `src/styles/tokens.css`, `src/app/globals.css`.
Add section A's breakpoints, fluid type scale, fluid spacing, `--content-max`, the `.page-shell`
helper; replace hardcoded `body{font-size:15px}` with the fluid body token. Do not restyle
components yet.
- **DoD:** `pnpm typecheck` + `pnpm lint` green; `pnpm build` succeeds (CSS compiles).
  Commit: `feat(web): responsive breakpoint + fluid type/spacing tokens`.

### Task 3 — Install motion + primitives

**Files:** `package.json` (`pnpm add motion`), `src/lib/motion/springs.ts`,
`src/lib/motion/use-reduced-motion-safe.ts`, `src/components/motion/{Reveal,RevealGroup,Pressable,Sheet}.tsx`.
Implement section B exactly. Add a tiny vitest for `use-reduced-motion-safe` (returns
opacity-only variants when reduced).
- **DoD:** `pnpm typecheck` + `pnpm lint` + `pnpm test` green. Commit:
  `feat(web): motion primitives (motion/react) with reduced-motion support`.

### Task 4 — Responsive layout shell

**Files:** `src/components/layout/{desktop-sidebar,mobile-tabbar,top-bar}.tsx`, app shell.
Apply `.page-shell` / fluid container to the main content; keep sidebar at `md+` and tabbar at
`<md` but make the content gutters fluid and verify the **tablet/mid-window (768–1024)** range
isn't pinched (fluid max-width + gutters). Add a `Reveal` to route content mount (subtle).
- **DoD:** `pnpm typecheck`+`pnpm lint`+`pnpm build` green. Commit:
  `feat(web): fluid responsive layout shell`.

### Task 5 — New-program chooser (entry for every create)

**Files:** `src/components/programs/onboarding.tsx`, `src/app/(app)/programs/new/page.tsx`,
library "New program" links. Per `tasks/redesign/02-programs-screens.md §2`: two editorial choice
cards (Follow a template / Build your own); the chooser is the entry point for *every* create, not
first-run only. `Reveal` the cards. `/programs/new` renders the chooser; "Build your own" creates
the blank draft and routes to the builder.
- **DoD:** typecheck+lint green; visual check the chooser renders. Commit:
  `feat(web): new-program chooser as the single create entry`.

### Task 6 — Builder: slot rail + mesocycle controls (`02 §6`)

**Files:** `program-builder.tsx`, `exercise-editor-row.tsx`, `intensity-mode-control.tsx`, `programs.css`.
- Left rail becomes a **draggable slot rail** using motion `Reorder.Group/Item`; each slot shows
  name + rest toggle; "+ Add slot" appends (springs in); live "N-slot microcycle" from slot count.
- Rest slot hides the exercise list → "Rest day, no exercises" (cross-fade).
- Details panel: when periodization set, show **Mesocycle length (microcycles, deload excluded)**
  bound to `mesocycle_length_microcycles` + an `Auto-deload` toggle. Editable on template-derived
  programs too.
- Activation enabled whenever ≥1 training slot exists; remove the `days.length !== days_per_week`
  check + error banner.
- **DoD:** typecheck+lint+test green; reorder works (visual). Commit:
  `feat(web): builder slot rail, rest toggle, mesocycle controls`.

### Task 7 — Active-program spine (`02 §3`)

**Files:** `active-program.tsx`, `program-masthead.tsx`, `mesocycle-bar.tsx`, `today-card.tsx`,
`week-list.tsx`, `program-overview.tsx`.
- Masthead meta: "8-slot cycle, 6 training" (microcycle), goal, intensity — not days_per_week.
- Cycle bar: one cell per **microcycle repetition** (done filled / current outlined / future
  empty) + trailing dashed **deload** cell when `auto_deload`; label "Cycle 2 of 4" from
  `mesocycle_length_microcycles`. Animate fill on mount.
- Today card: the slot at the rotation position (`usePosition`); rest slot → quiet "Rest day" +
  next training slot named; Start for training slots.
- Microcycle list (rename week-list concept): one row per slot; rest rows italic/muted; training
  rows show name, muscle summary, count, status (Done/Today/Planned).
- `RevealGroup` staggers the spine on load.
- **DoD:** typecheck+lint green; spine renders against a seeded active program (visual). Commit:
  `feat(web): active-program spine on rotation position + cycle bar`.

### Task 8 — Library: activate/deactivate, duplicate, save-as-template (`02 §4,§5`)

**Files:** `program-library.tsx`, a new `save-as-template-dialog.tsx`, `programs.css`.
- Row meta: microcycle + mesocycle length + goal. Inactive → Activate; active → "Active" that
  on hover/focus swaps to destructive **Deactivate**; on touch the same via an overflow control.
- Overflow per row: **Duplicate** (`duplicateProgram` → lands on the copy) and **Save as
  template** (dialog: name + visibility Private/Shared → `saveAsTemplate`). Dialog uses `Sheet`/
  `AnimatePresence`. Keep trash-delete separate.
- Full-width dashed "Create a new program" → the chooser (Task 5).
- **DoD:** typecheck+lint+test green. Commit:
  `feat(web): program library activate/deactivate, duplicate, save-as-template`.

### Task 9 — Supporting screens (`02 §7`)

**Files:** `browse-templates.tsx`, `template-detail.tsx`, `per-day-detail.tsx` (slot detail).
- Browse: group gallery into **Curated / My templates / Shared by partners**; meta shows
  microcycle + mesocycle length; user-saved carry an owner/visibility marker + delete-own; all use
  "Use this template".
- Template detail: hero, spec strip, **slot-by-slot** breakdown, "Use this template" → copy → new
  editable program.
- Per-slot detail: slot hero, per-exercise Sets/Reps/intensity/Rest, Start; rest slots show rest.
- **DoD:** typecheck+lint green. Commit: `feat(web): templates browse/detail + slot detail on new model`.

### Task 10 — Responsive + motion polish, full green, visual verification

**Files:** `programs.css` and any surface needing breathing room.
- Sweep `programs.css`: replace fixed `max-w-*`/pinched widths with `.page-shell`; raise spacing
  to the fluid rhythm; verify every grid reflows cleanly at **mobile / tablet (768–1024) /
  desktop**; bump base/figure sizes within the brief ranges.
- Confirm reduced-motion path on every animated surface.
- **DoD (final gate):** `pnpm typecheck` + `pnpm lint` + `pnpm test` + `pnpm build` ALL green.
  Commit: `feat(web): programs responsive + motion polish`.
- **Visual verification (orchestrator, not the loop):** run the app, screenshot the spine,
  builder, library, browse, and template detail at **390px / 834px / 1440px**, light + dark, and a
  short screen recording of the slot-rail reorder + cycle-bar load.

---

## Acceptance (rolls up `02-programs-screens.md §8` + `03/04` responsive bullets)

- [ ] `pnpm typecheck`/`lint`/`test`/`build` all green (web restored + redesigned).
- [ ] Programs surfaces breathe at all widths; explicit tablet/mid-window layout; no pinched mastheads.
- [ ] New program opens empty; chooser offers template-or-blank on every create.
- [ ] Builder slot rail adds/reorders/rest-toggles; live microcycle length; activates on ≥1 training slot.
- [ ] Periodization exposes mesocycle length (deload excluded) + auto-deload; editable on copies.
- [ ] Cycle bar counts microcycle repetitions + deload cell.
- [ ] Library: deactivate by hover (pointer) or overflow (touch); duplicate; save-as-template w/ visibility.
- [ ] Browse groups Curated / Mine / Shared; template + slot detail on the new model.
- [ ] Motion is restrained + physical and fully honors `prefers-reduced-motion`.
- [ ] Verified light + dark at phone, tablet, and desktop (screenshots attached).

## Out of scope (later)
- Programs **iOS** port (after this web shape settles — separate plan).
- Other surfaces (Today, Workouts, Health, Insights, Nutrition) — this plan is Programs only.
