# Programs redesign (Direction A) + first-run onboarding + multi-program — Claude Code package

Implement the **Programs** experience in `apps/web` (Next.js) and `apps/ios`
(SwiftUI). Pairs with `claude-code-editorial-handoff.md` (web system) and
`claude-code-editorial-ios.md` (iOS system) — do those first; this covers only
the programs-specific screens. Same pattern as `claude-code-nutrition-A.md`.

**Visual source of truth:** `programs/index.html` in the design project — focus
the **"A · Training spine"** frames, the **First run** frames, and the
**Supporting screens** (templates, detail, per-day, builder). Backed by
`programs/screens.jsx` and `programs/programs.css`.

Mock used throughout: **Alex Chen · PPL — Vanilla 6-day · Week 4 of 8 · Push A today.**

---

## 0. Concept (mirror the nutrition flow)

| | Old programs page | New (Direction A) |
|---|---|---|
| First action | land on a list | **first-run choice**: Follow a template vs Build your own |
| Main screen | template/list grid | **active-program "spine"**: masthead + mesocycle bar, today's session, this week, then a **My programs** library |
| Multiple programs | implicit | first-class — **create, activate, delete** several programs |
| Builder reps | single rep field | **per-exercise Range ↔ Target** toggle |
| Builder intensity | per-exercise | **global program setting** (RPE / RIR / Off); each exercise shows a target value under the chosen scale |

Two onboarding modes set on first run, stored as `programSetupMode`-style intent:
- **Follow a template** → browse gallery → template detail → "Use this template"
  copies it to a new active program.
- **Build your own** → the builder with a blank program.

---

## 1. Data model notes (confirm/extend; no behavior change)

- A user can have **many programs**; exactly one is `active`. Others are
  `inactive` or `archived`. Need: list endpoint, `activate(programId)`,
  `delete(programId)`, `create()`.
- A **program** has: `name`, `goal`, `progressionStrategy`, `weeks`,
  `deloadWeek?`, an ordered list of **days**, and a program-level
  **`intensityMode: "rpe" | "rir" | "off"`** (NEW — see §5).
- A **day** has `name` + ordered **exercises**.
- An **exercise** has `name`, `muscle`, `sets`, and:
  - `repMode: "range" | "target"` (NEW) with `reps` (e.g. `"6–8"` or `"12"`),
  - `intensityTarget` (a value like `"8"` or `"1–2"`) interpreted via the
    program's `intensityMode`. **No per-exercise intensity mode.**
- First-run gate: show onboarding when the user has **no programs yet**.

These are additive (`intensityMode`, `repMode`). Don't change progression logic.

---

## 2. First-run onboarding

Route gate in `app/(app)/programs/page.tsx`:
```
if (user.programs.length === 0) → <ProgramsOnboarding />
else → <ActiveProgramView />
```
**`components/programs/onboarding.tsx`** — centered editorial, two choice cards
(match `WebOnboard`/`IosOnboard`, reuse the `.ow-card` / `.pi-ecard` look from
the nutrition onboarding spec):
- Kicker `WELCOME TO PROGRAMS`; serif H1 "How do you want to train?"; sub
  "First time here — start from a proven template, or build your own. You can switch anytime."
- **Card 1 (primary, ink):** `RECOMMENDED` · **Follow a template** · "Pick a
  proven program — PPL, Upper/Lower, 5/3/1 and more. Copy it, tweak if you like,
  and start this week." → routes to **Browse templates** (§6).
- **Card 2 (outline):** `FULL CONTROL` · **Build your own program** · "Compose
  days, exercises, set/rep schemes and a progression strategy from a blank
  slate." → routes to the **Builder** (§5) with an empty program.

iOS: `ProgramsOnboardingView`, same two cards, shown when `programs.isEmpty`.

---

## 3. Active-program overview — Direction A (web)

`components/programs/active-program.tsx` (+ subcomponents). Top→bottom:

1. **Masthead** (`.aw-mast`) — `ACTIVE PROGRAM` kicker, serif program name, and a
   right-aligned meta row (Goal / Strategy / Frequency). Below it a **mesocycle
   bar** (`.meso`): one cell per week — completed (filled accent), current
   (accent outline), future (empty), deload (dashed). Label "Week 4 of 8".
2. **Today card** (`.aw-today`) — hairline-bordered block: `TODAY · TUESDAY`
   kicker, serif day name (Push A), exercise summary, big **Start** button.
3. **This week** (`.aw-week`) — section rule + "Full calendar" link, then one row
   per day (`.aw-day`): dow, serif name + muscle summary, exercise count, status
   (`Done` muted-sage / `Today` accent / `Planned`). Completed rows dimmed; rest
   days italic muted.
4. **My programs** (§4).

Header action: an `Edit` button → builder for the active program.

## 4. My programs library (multiple + delete)

Below the week (`.aw-progs`):
- Section rule "My programs" + **"+ New program"** link (header) → builder, blank.
- One row per program (`.aw-prog-row`): serif name (active in accent) + meta
  (`Week 4 of 8 · hypertrophy`), a right-side action (**Active** label, or
  **Activate** / **Restore** for archived), and a **trash** button that turns
  destructive-red on hover → confirm dialog → `delete(programId)`.
- A full-width dashed **"+ Create a new program"** button at the end.

**iOS** (`ActiveProgramView`): same order. The program library uses
**swipe-to-delete** (trailing red Delete action) instead of a trash button;
"Activate"/"Active" trailing label; a "+ Create a new program" row.
Match `.pia-*` classes.

---

## 5. Builder / editor

`components/programs/program-builder.tsx` + `ProgramBuilderView`.

**Web layout** (`.ew-grid`): left column = draggable **day rail** (`.ew-dtab`,
grip handles, "+ Add day") + a **Details** panel; right column = the selected
day's exercise list.

**Details panel — program-level settings:**
- Goal, Progression strategy, Weeks (as today).
- **Intensity tracking** (NEW, GLOBAL): an `RPE / RIR / Off` segmented
  (`.mini-seg`) — **one choice for the whole program**, caption "Applies to every
  exercise in the program." Persists to `program.intensityMode`.

**Exercise rows** (`.ew-ex`): grip + name + muscle + delete (trash). A control
row (`.ew-ctl`) with labeled groups:
- **Sets** — number field.
- **Reps** — a `Range / Target` segmented (`.mini-seg`) bound to
  `exercise.repMode`; the adjacent field shows a span ("6–8") in range mode or a
  single number ("12") in target mode.
- **{RPE|RIR} target** — shown **only when** `program.intensityMode !== "off"`;
  label derives from the global mode; the field holds `exercise.intensityTarget`.
  When global mode is Off, this group is hidden entirely.
- "+ Add exercise to {day}" dashed button.

**iOS** (`ProgramBuilderView`): a horizontal **day rail** (`.pie-dtab`), then a
full-width **"Intensity tracking · Whole program"** card (`.pie-global`) with the
`RPE/RIR/Off` segmented, then exercise blocks (`.pie-ex`) each with Sets, a
`Range/Target` segmented + value, and (when not Off) the intensity target value.
Drag handles on each; "+ Add exercise".

> The `.mini-seg` / `.ios-mini-seg` is a compact segmented (ink-filled active
> segment). Build it as a small reusable control.

---

## 6. Supporting screens

- **Browse templates** (`.tw-*` / `.pit-*`): underline category filters
  (All / Hypertrophy / Strength / Endurance / General) + a gallery of template
  cards (label, serif name, description, weeks / freq / users meta; active one
  marked). Tap → template detail.
- **Template detail** (`.dw-*` / `.pid-*`): serif hero (label, name, description),
  a spec strip (weeks / per-week / goal / rating), the day-by-day breakdown
  (exercise + scheme), and a primary **"Use this template"** CTA (iOS: pinned
  bottom bar) → copies to a new active program.
- **Per-day detail** (`.xw-*` / `.pix-*`): day hero (Day n · split · week), then
  each exercise with a Sets / Reps / {RPE|RIR} / Rest scheme row and a
  "Progression — …" line. A **Start workout** action.

---

## 7. Acceptance checklist

- [ ] New account (no programs) → **onboarding** (Follow a template / Build your own).
- [ ] Overview leads with masthead + **mesocycle bar** (completed / today / deload), today card, week list.
- [ ] **My programs** lists all programs; can **activate**, **delete** (web trash + confirm; iOS swipe), and **create** new ones.
- [ ] Builder: per-exercise **Range ↔ Target** reps toggle works and changes the value display.
- [ ] Builder: **intensity is a single global** RPE/RIR/Off control (Details on web, "Whole program" card on iOS); per-exercise rows show only a target under the chosen scale, and hide it entirely when Off.
- [ ] Template flow: browse → detail → "Use this template" creates an active program.
- [ ] Editorial system honored (serif titles+figures, hairlines, clay accent, no shadows) in light + dark on every screen.
- [ ] Diff against the matching frames in `programs/index.html` at desktop + iPhone widths.

## 8. Out of scope

- Progression-engine math, calendar scheduling, and the active-workout logger (separate features).
- Reordering persistence backend (wire dnd to existing endpoints; UI only here).
- Component APIs otherwise unchanged — only class strings / tokens / the two new fields.
