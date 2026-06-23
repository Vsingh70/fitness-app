# Programs screens

Web UI built on the model in `01-program-model.md`. Existing components live in
`apps/web/src/components/programs/`; this spec changes their data shape and fixes the
documented bugs. Keep the editorial system in `00-overview/design-system.md`.

## 0. Bugs this must fix

From `archive/programs-workflow-original-feedback.md`:

1. Content feels cramped and non-responsive. Raise the spacing scale and the base
   type size; let containers breathe at wider viewports.
2. New programs are hard-set to 6 weeks and 4 days, and activation throws "Program
   has 0 days but 4 are required". The new program starts empty and activates on any
   training slot. The hard-coded defaults in `app/(app)/programs/new/page.tsx`
   (`weeks: 6, days_per_week: 4`) are removed.
3. Picking periodization must surface a control for mesocycle length, deload excluded.
4. Microcycle length and mesocycle length must be editable on a template-derived
   program.
5. An active program has no off switch. Add a hover-to-deactivate affordance.

## 1. Spacing and type tuning (bug 1)

- Audit the Programs surfaces against `tokens.css`. Increase the page max-width and
  the vertical rhythm so rows and mastheads are not pinched. Make the layout fluid up
  to the content max-width rather than fixed and narrow.
- Bump base body and figure sizes within the ranges in the design brief (bodies 15 to
  17, headlines 22 / 28 / 34). Do not introduce new tokens; tune the existing scale.
- Verify at iPhone width and desktop, light and dark.

## 2. New-program choice (first run and every time after)

`components/programs/onboarding.tsx`. Two editorial choice cards:

- Card 1 (primary): Follow a template, routes to Browse templates.
- Card 2 (outline): Build your own, routes to the builder with a blank program (empty
  slot list, no forced length).

This chooser is **not** first-run only. It is the single entry point for creating any
program. On first run (zero programs) it is the whole screen. Once the user has
programs, the same chooser is reached from every "New program" / "Create a new
program" action in the library (section 5) and from the active spine's header.

Implementation note: the current "New program" links route straight to
`/programs/new`, which silently creates a blank program. Repoint them at the chooser
(for example a `/programs/new` that renders the two-card choice, with "Build your own"
being the action that then creates the blank draft). The goal: a user who already has
programs can still start a new one from a template, not only from scratch.

## 3. Active-program spine

`components/programs/active-program.tsx` and subcomponents. Top to bottom:

1. **Masthead** (`program-masthead.tsx`): `ACTIVE PROGRAM` kicker, serif name, meta
   row. Replace the `days_per_week` line with microcycle length, for example
   "8-slot cycle, 6 training". Goal and intensity mode stay.
2. **Cycle bar** (`mesocycle-bar.tsx`): rework from weeks to microcycle repetitions.
   One cell per repetition in the mesocycle (completed filled, current outlined,
   future empty), with a trailing dashed deload cell when `auto_deload` is true.
   Label "Cycle 2 of 4" using `mesocycle_length_microcycles`, not weeks.
3. **Today card** (`today-card.tsx`): the slot at the current rotation position. If
   the position is a rest slot, show a quiet "Rest day" state with the next training
   slot named. Start button begins the session for a training slot.
4. **This microcycle** (`week-list.tsx`, rename concept to microcycle): one row per
   slot in the current microcycle. Rest slots render italic and muted; training slots
   show name, muscle summary, exercise count, and status (Done, Today, Planned).
5. **My programs** (`program-library.tsx`): see section 5.

Header action: Edit routes to the builder for the active program.

## 4. Activate and deactivate (bug 5)

In `program-library.tsx` rows and the active masthead:

- An inactive program shows an `Activate` button (calls `POST /activate`).
- An active program shows an `Active` label that, on hover or focus, swaps to a
  `Deactivate` action in the destructive tone, calling `POST /deactivate`. On touch,
  where hover does not exist, expose the same action via the row's overflow control so
  it is reachable without a pointer.
- Deactivation does not delete; the program drops to inactive and keeps its position.
- Keep the existing trash-to-confirm delete flow separate from deactivate.

## 5. My programs library

`program-library.tsx`. One row per program: serif name (active in accent), meta line
now reading microcycle and mesocycle length plus goal (for example
"8-slot cycle, cycle 2 of 4, hypertrophy"). Right side carries Activate or the
Active/Deactivate affordance from section 4, plus the trash delete. A full-width
dashed "Create a new program" button at the end routes to the **new-program chooser**
(section 2), so a template is always an option, not just a blank build. The header
"+ New program" link routes there too.

Each row also exposes, via an overflow control to avoid crowding the row:

- **Duplicate** — calls `POST /programs/{id}/duplicate` and lands on the new editable
  copy (named "... (copy)", inactive). A fork of the program with no template link.
- **Save as template** — opens a small dialog with a name field and a visibility
  choice (Private to me / Shared with partners), then calls
  `POST /programs/{id}/save-as-template`. The program is unchanged; the new template
  appears in Browse templates (section 7).

These two also appear in the builder header so a program can be duplicated or saved as
a template while editing it.

## 6. Builder (bugs 2, 3, 4)

`program-builder.tsx` plus `exercise-editor-row.tsx`,
`intensity-mode-control.tsx`, `mini-segmented.tsx`.

Left column: a draggable **slot rail** (was the day rail). Each slot shows its name
and a rest toggle; "+ Add slot" appends a slot. Removing the `days_per_week` gate, the
microcycle length is simply the number of slots; show it live ("8-slot microcycle").

Right column: the selected slot's exercise list. A slot marked as rest hides the
exercise list and shows "Rest day, no exercises".

Details panel (program-level):

- Goal, periodization mode, intensity mode (RPE / RIR / Off, global, as today).
- **Mesocycle length** control (bug 3): when periodization is set, show a numeric
  field "Mesocycle length, in microcycles (deload excluded)" bound to
  `mesocycle_length_microcycles`, with an `Auto-deload` toggle beside it.
- These controls are editable on any program, including template-derived ones
  (bug 4); there is no locked structure on copies.

Exercise rows keep the migration-0026 controls: Sets, a Range/Target reps toggle
(`rep_mode`), and a single intensity target shown only when intensity mode is not Off.

Activation control in the builder calls `POST /activate` and is enabled whenever at
least one training slot exists; remove the `p.days.length !== p.days_per_week` check
and its error banner.

## 7. Supporting screens

- **Browse templates** (`browse-templates.tsx`): category filters and a gallery.
  Template meta shows microcycle length and mesocycle length, not weeks/days_per_week.
  Group the gallery into Curated, My templates (the user's own, private and shared),
  and Shared by partners. User-saved templates carry a small owner/visibility marker;
  the user can delete their own. All use the same "Use this template" copy flow.
- **Template detail** (`template-detail.tsx`): hero, spec strip, slot-by-slot
  breakdown, and "Use this template" which calls the copy endpoint and lands on the
  new editable program.
- **Per-slot detail** (`per-day-detail.tsx`, rename concept to slot): slot hero, each
  exercise's Sets / Reps / intensity / Rest, and a Start workout action. Rest slots
  show the rest state.

## 8. Acceptance

- [ ] Programs surfaces breathe at all widths; no cramped masthead or rows.
- [ ] New program opens empty; no 6-week or 4-day defaults anywhere in the flow.
- [ ] Creating a program when one already exists still offers the template choice, not
      only a blank build.
- [ ] A program can be duplicated from the library or builder into a new editable copy.
- [ ] A program can be saved as a template with a name and visibility; it then appears
      in Browse templates and is usable via "Use this template".
- [ ] Builder adds, reorders, and rest-toggles slots; microcycle length tracks live.
- [ ] Activation works with any training-slot count; the old error banner is gone.
- [ ] Periodization exposes mesocycle length (deload excluded) and an auto-deload toggle.
- [ ] Mesocycle and microcycle length are editable on template-derived programs.
- [ ] Active programs can be deactivated by hover (pointer) or overflow (touch).
- [ ] Cycle bar counts microcycle repetitions with a deload cell, not weeks.
- [ ] Light and dark verified at iPhone and desktop widths.
