# Nutrition redesign (Direction A) + First-run onboarding — Claude Code package

Implement the **Direction A "Log-first"** nutrition experience and the
**first-run onboarding** in `apps/web` (Next.js) and `apps/ios` (SwiftUI).
Pairs with `claude-code-editorial-handoff.md` (web system) and
`claude-code-editorial-ios.md` (iOS system) — those define the editorial tokens,
serif typography, hairline surfaces, and clay accent this builds on. **Do those
first**; this doc only covers the nutrition-specific screens.

**Visual source of truth:** `nutrition/index.html` in the design project
(open it, focus the "A · Log-first" frames and the "First run" frames). Backed by
`nutrition/screens.jsx` (`WebDirA`, `IosDirA`, `WebEntry`, `IosEntry`,
`WebAddMeal`, `IosAddMeal`, `WebTrends`, `IosTrends`) and `nutrition/nutrition.css`.

---

## 0. The concept (what changed from the old nutrition page)

| | Old | New (Direction A) |
|---|---|---|
| Lead element | macro ring + bars | **slim calorie masthead + huge quick-add search** |
| First action | scroll to a meal, tap + | type/scan/snap from the top, or tap a **recent-food chip** |
| Meals | fixed **Breakfast / Lunch / Snack / Dinner** | **no presets** — meals come from the user's **meal plan**, or are added freely ("Meal 1, 2, 3 … + Add meal") |
| Macros | ring only | **calorie figure + P / C / F strip** (carbs & fat now first-class, incl. iOS) |
| Entry | straight to the logger | **first-run onboarding**: Flexible tracking vs Create a meal plan |

Two tracking modes the data model must support:
- **Flexible** (default, no plan): user adds any number of meals per day; meal
  "slots" are not predefined. Display them as `Meal 1…n` (or a user-typed name).
- **Plan-based**: an active meal plan defines an ordered list of meals
  (e.g. *Pre-workout, Post-workout, Dinner*); the day renders exactly those
  slots, each fillable. **Never render hard-coded Breakfast/Lunch/Snack/Dinner.**

---

## 1. Data model notes (confirm/extend, don't break behavior)

Whatever the current nutrition schema is, the UI assumes:

- A **day** has an ordered list of `meals`; each meal has an optional `name`
  (nullable → render `Meal {index+1}`), optional `time`, and a list of
  `entries` (food + grams + computed kcal/p/c/f).
- A **MealPlan** (optional, per user/active): ordered `slots` with a `name` and
  optional target macros. When a plan is active, the day is seeded from its
  slots; meal count = slot count and the "+ Add meal" affordance is hidden
  (or shown as "+ Add extra meal" — your call, default hidden).
- A user preference `nutritionMode: "flexible" | "plan"` set during onboarding,
  switchable in Settings. Default unset → show onboarding.
- Daily targets: `kcal, protein_g, carbs_g, fat_g` (already exist for the ring).

No API/business-logic changes beyond exposing `nutritionMode` and the
nullable meal `name`/plan slots if not already present.

---

## 2. First-run onboarding

**Route (web):** `app/(app)/nutrition/page.tsx` should branch:
```
if (!user.nutritionMode) → <NutritionOnboarding />
else → <NutritionDay />
```
Or a dedicated `app/(app)/nutrition/welcome/page.tsx` that redirects back once a
choice is made. Show it the **first time the user opens Nutrition after signup**
(gate on `nutritionMode == null`, not a one-time flag you can't reset).

**Component:** `components/nutrition/onboarding.tsx`
Centered, editorial, two choice cards (match `WebEntry`/`IosEntry`):

- Kicker: `WELCOME TO NUTRITION`
- Serif H1: "How do you want to track?"
- Sub: "First time here — pick a way to get started. You can switch anytime in settings."
- **Card 1 (primary, ink fill):** kicker `RECOMMENDED` · title **Flexible tracking** ·
  body "Log meals freely as you eat — search, scan a barcode, or snap a photo.
  Add as many meals a day as you like. No setup." · CTA "Start tracking →"
  → sets `nutritionMode = "flexible"`, routes to the day logger.
- **Card 2 (outline):** kicker `STRUCTURED` · title **Create a meal plan** ·
  body "Build a daily template with a set number of meals and macro targets,
  then log against it each day." · CTA "Build a plan →"
  → sets `nutritionMode = "plan"`, routes to the meal-plan builder
  (stub a `MealPlanBuilder` route if it doesn't exist yet; out of scope to fully build).

Card spec: `border border-border-strong rounded-[6px] p-[22px]`, hover
`border-text`; primary card `bg-text text-bg`. Kicker = uppercase tracked 11px;
title = serif 26px/500; body = 13px secondary; CTA = uppercase tracked 12px with
arrow. See `.entry-card` in `nutrition.css`.

**iOS:** `NutritionOnboardingView` shown when `nutritionMode == nil`. Same two
cards (`.ni-ecard` styling): primary uses `Color.ink`/paper, the other a
hairline border. Large serif title "How do you want to track?".

---

## 3. Main day screen — Direction A (web)

`components/nutrition/nutrition-day.tsx` (+ small subcomponents). Layout
top→bottom, all token/utility classes from the editorial system:

**1. Calorie masthead** (`.aw-progress`) — a serif figure row over a 2px ink rule:
```
<div className="flex items-baseline gap-[18px] border-b-2 border-text pb-3.5">
  <span className="font-serif text-[52px] font-medium leading-[0.95] tracking-[-0.03em] tabular-nums">1,620</span>
  <span className="text-text-tertiary text-base">of 2,680 kcal · 1,060 left</span>
  <div className="ml-auto flex gap-[22px]">{P/C/F columns}</div>
</div>
```
Each macro column: serif value `text-[22px]` + tiny uppercase label
(`Protein/Carbs/Fat`). **Carbs and fat are required here.**

**2. Quick-add bar** (`.aw-search`) — the hero action, `h-14`, `1.5px` ink border,
serif placeholder "What did you eat?", trailing clay **+** button. Opens the
add-meal flow (§5). To its right/below, a "Scan · Photo" affordance.

**3. Recent & frequent** (`.aw-recent`) — a wrap of tappable food chips
(`.aw-chip`): name + serif kcal + a small ink **+**. Tapping logs that food in
one tap. Source from the user's most-logged + recent foods.

**4. Meals list** (`.aw-meals`) — render the day's meals (plan slots or
flexible). Each row (`.aw-meal`): a `96px` "when" column (serif meal name +
uppercase time), the entry lines (food · grams, with kcal), and a right-aligned
serif kcal total with a clay "{p}g protein" subline.
- **Flexible mode:** names are `Meal 1…n`; after the list show a full-width
  dashed **+ Add meal** button (`.AddMealBtn`, non-ios variant).
- **Plan mode:** names come from the plan slots; empty slots show a muted
  "+ Add food" inline; **hide** the global "+ Add meal" (count is fixed).

Header action (top bar): a `Day · Week` segmented control linking to Trends (§6).

---

## 4. Main day screen — Direction A (iOS)

`NutritionDayView` (SwiftUI). Same order:

1. **Masthead:** large-title-style serif "Today" with a `Tuesday · May 27`
   kicker, then the big serif calorie figure `1,620` + `/ 2,680 · 1,060 left`.
2. **Macro strip** (`.nia-macros`): three columns, each a top hairline rule +
   tiny uppercase label + serif `value/targetg`. **Protein 134/200 · Carbs
   168/300 · Fat 51/80** — carbs & fat must appear (this was the gap in the old iOS screen).
3. **Quick-add** (`.nia-search`): 52pt, 1.5pt ink border, serif placeholder,
   trailing clay + tile. Tapping presents the add-meal sheet (§5).
4. **Recent chips** (`.nia-recent`): horizontal scroll of hairline pills.
5. **Meals** (`.nia-meal`): name + time + comma-joined items on the left, serif
   kcal + `{p}g P` on the right, hairline separators. Then the dashed
   **+ Add meal** button (`.AddMealBtn ios`) in flexible mode; plan slots in plan mode.

Use `Color.ink` for the calorie figure, serif (`.serif`) + `.monospacedDigit()`
throughout. No filled cards — hairlines + whitespace.

---

## 5. Add-meal flow (search / scan / photo)

Keep the existing search/scan/photo behavior; restyle to editorial and route the
result into the **target meal** (a plan slot, an existing flexible meal, or a new
one created by "+ Add meal").

- **Web** (`WebAddMeal`): full page or modal — serif title "Add to {meal name}",
  ink underline tabs `Search / Scan barcode / Photo`, a 1.5px-bordered search
  box, then food result rows (name + USDA/brand meta + serif kcal + outline **+**).
- **iOS** (`IosAddMeal`): a bottom **sheet** (`.ni-sheet`) with a grabber, serif
  title, underline tabs, search field, and result rows with a circular outline
  **+**. Match `.ni-sheet` / `.ni-fr`.

"Scan" → barcode camera; "Photo" → the existing vision/Ollama estimate flow,
restyled. The food row's **+** adds to the chosen meal and dismisses.

---

## 6. Trends (day / week)

`components/nutrition/nutrition-trends.tsx` + `NutritionTrendsView`. Underline
toggle `Day / Week / Month`. Week view = 7 bars vs a dashed target line
(`.tw-week` / `.nit-week`): under-target bars muted, over-target ink, today clay.
Below, a stat band (`.tw-stat`): Avg/day, Avg protein, Days on target (`5/7`),
Adherence (`86%`) — serif figures, top hairline rules. Use Swift Charts on iOS
(`BarMark` clay, `RuleMark` dashed target) and recharts on web (already themed).

---

## 7. Acceptance checklist

- [ ] New account → Nutrition shows **onboarding** (Flexible vs Create a meal plan); choosing sets `nutritionMode` and never shows again unless reset.
- [ ] **No** hard-coded Breakfast/Lunch/Snack/Dinner anywhere.
- [ ] Flexible mode: "+ Add meal" adds unlimited meals (`Meal 1…n`).
- [ ] Plan mode: meal count = plan slots; "+ Add meal" hidden.
- [ ] Calorie masthead + **P/C/F** strip on **both** web and iOS (carbs & fat visible on iOS).
- [ ] Quick-add search is the visual lead; recent-food chips log in one tap.
- [ ] Add-meal (search/scan/photo) routes into the correct meal; iOS uses a bottom sheet.
- [ ] Trends day/week renders against target; stat band correct.
- [ ] Editorial system honored (serif figures, hairlines, clay accent, no shadows) in light + dark.
- [ ] Diff against the `A · Log-first`, `First run`, and `Flows` frames in `nutrition/index.html` at desktop + iPhone widths.

## 8. Out of scope

- The full meal-plan **builder** UI (stub the route; structured-mode users land there).
- Barcode/vision backend behavior — reuse as-is, restyle only.
- Switching `nutritionMode` UI in Settings (add a single row; full settings polish later).
