# Design brief

For Claude Design (or any designer onboarding to gym-app). This is the
single document that, together with `tasks/00-overview/design-system.md`
and `CURRENT-STATE.md`, gives you everything you need to design UX for
the web app and the iOS app.

Read order if you have 10 minutes:
1. This file end-to-end.
2. `tasks/00-overview/design-system.md` (canonical design language).
3. `CURRENT-STATE.md` (what is built vs deferred).

Read order if you have an hour:
4. `tasks/00-overview/api-conventions.md` (request/response shape).
5. `tasks/00-overview/data-model.md` (entities and enums).
6. `apps/web/src/styles/tokens.css` (real, implemented tokens).
7. Skim `apps/web/src/components/` (existing component vocabulary).

---

## 1. Project at a glance

**gym-app** is a personal fitness app for a single developer and a few
gym buddies. Two surfaces:

- **iOS app** (SwiftUI, SF Symbols, iOS 17+). Primary surface for daily
  use: workouts, quick meal logging, today screen with readiness.
- **Web app** (Next.js 15 App Router, React 19, Tailwind v4 CSS-first
  config). Secondary surface for program building, analytics, history
  browsing on a larger screen.

**Audience.** Power users who already know how to lift. They want
- fast, low-friction logging during a workout (a thumb-only interaction
  pattern on iOS, keyboard-driven on web);
- meaningful trends and progressive overload nudges, not generic advice;
- the option to ignore every recommendation without the UI nagging them.

**Non-goals.** No social feed, no public profiles, no marketplace, no
gamification (no streaks, no XP, no badges). Numbers tell the story.

**Tone.** Confident, quiet, athletic. No exclamation points, no emoji,
no "Great job!" copy. Errors are matter-of-fact ("Couldn't reach
Fitbit — try again"), success is implicit ("Saved").

---

## 2. Architecture summary

### Backend (`apps/api`)
- FastAPI + SQLAlchemy 2.0 async + Postgres 16 + Redis 7.
- ~80 endpoints under `/v1/`. Snake_case JSON. ISO 8601 UTC `Z`
  timestamps. Cursor pagination only.
- AI: local Ollama (text only). Used for progression rationales and
  weekly insights. Heavy work is queued. There is no vision model and no
  meal photo recognition (that feature was dropped).
- Auth: Apple/Google ID token → `POST /v1/auth/exchange` → JWT access
  (15 min) + opaque rotating refresh token (30 day).
- Error envelope: `{"error": {"code", "message", "details?"}}`. Codes
  the UI must handle: `validation_error`, `not_found`, `unauthorized`,
  `forbidden`, `conflict`, `rate_limited`, `integration_error`,
  `internal_error`.
- Rate limits the UI must surface: 60/hour for AI endpoints; 600/min
  per user for everything else. Show a friendly "give it a minute"
  state, not a raw 429.

### Web (`apps/web`)
- Next.js 15 App Router, React 19, TypeScript strict.
- TanStack Query for server cache, Zustand for client UI state, dnd-kit
  for program day reordering, framer-motion sparingly.
- Tailwind v4 (CSS-first, no `tailwind.config.ts`). Tokens live in
  `apps/web/src/styles/tokens.css` and are referenced as
  `var(--color-bg)`, `var(--radius-card)`, etc.
- Routes are split into route groups: `(auth)/sign-in`,
  `(auth)/callback`, and `(app)/*` (everything authed).

### iOS (`apps/ios`)
- SwiftUI app with the editorial design system and all feature screens
  (Today, Workouts, Programs, Nutrition, Insights, Settings) ported as a
  visual build. The live data layer (networking to the API) is not wired
  yet, so screens currently render against local sample data. iOS remains
  the primary surface; web mirrors its visual decisions.

### Source of truth for visual decisions
- iOS first. When iOS and web disagree, iOS wins. Web mirrors the iOS
  visual decisions even if it means importing an idiom (sheets, large
  titles, iOS-style segmented controls) that isn't native to the web.
- Where they must diverge: input modalities (keyboard shortcuts on web,
  haptics on iOS), navigation chrome (sidebar + tab bar on web, tab bar
  + nav stack on iOS).

---

## 3. Existing design language

This section duplicates the *load-bearing* parts of
`tasks/00-overview/design-system.md` so a designer can start without
opening another file. The spec file remains canonical.

### Inspiration
- **Editorial print** (magazine mastheads, serif figures, hairline
  rules, generous whitespace, color used sparingly).
- **Strong app** (set-row density, in-workout chrome that gets out of
  the way).
- **iOS system Health** (insights cards, segmented time-range pickers,
  large readable numbers).

Avoid: Strava-style social cards, MyFitnessPal density (it's too busy),
saturated system-blue chrome (we replaced that with warm paper and a
single clay accent).

### Typography
- A **display serif** sets titles and every figure. Web loads Source
  Serif 4 via next/font with a system serif fallback (Iowan Old Style,
  Palatino, New York, Georgia); iOS uses the New York system serif.
- Body, buttons, and form fields use the **system sans** (`--font-sans`,
  SF Pro Text leaning). Tiny labels are **uppercase mono kickers**.
- Every stat figure renders in the serif with tabular numerics so "187"
  and "188" line up. Do not bold the serif past medium (500).
- Headlines: 22 / 28 / 34. Bodies: 15 / 17. Captions: 12 / 13.
- Respect iOS Dynamic Type. On web, respect the user's browser font
  size preference; don't lock to `16px`.

### Color tokens (already implemented on web)

From `apps/web/src/styles/tokens.css`. The palette is warm paper and ink
in OKLCH; surfaces are flat with hairline borders, not shadows. Both
light and dark are implemented; `prefers-color-scheme` and an explicit
`[data-theme]` override both work. Each muted semantic tone has a `-soft`
variant for fills (e.g. `--color-accent-soft`).

Semantic tokens (use these — never raw hex/OKLCH):
- `--color-bg` — page background.
- `--color-surface` — card / list row.
- `--color-surface-elevated` — modal, sheet, popover.
- `--color-border` — hairlines.
- `--color-border-strong` — focus rings, dividers between sections.
- `--color-text` — primary text.
- `--color-text-secondary` — labels, captions.
- `--color-text-tertiary` — placeholder, disabled.
- `--color-text-inverse` — text on accent fill.
- `--color-accent` — user-chosen accent (default clay).
- `--color-accent-foreground` — text on accent.
- `--color-success` — completion, good readiness, PR.
- `--color-warning` — moderate readiness, deload nudge.
- `--color-destructive` — delete, error, low readiness.
- `--color-pr` — gold-leaning highlight for personal records.

Accent picker: Clay (default), Slate, Teal, Ochre, Rose; all muted. The
underlying `data-accent` keys stay blue/indigo/mint/orange/pink so the
picker plumbing is unchanged. User picks one in settings; the entire app
re-themes via `--color-accent`. Never hard-code the default accent.

### Radii
- `--radius-card: 4px` (web). iOS cards match the restrained radius.
- `--radius-button: 7px`.
- `--radius-sheet: 14px` (web modal corners; iOS bottom sheet uses the
  same radius at the top corners only).

### Motion
- iOS spring: `response 0.4, damping 0.85`. This is the *only* spring
  unless there is a reason.
- Web easing: `--motion-spring: cubic-bezier(0.32, 0.72, 0, 1)` for
  sheet/drawer enter; 200 ms for most transitions; 400 ms for sheet
  enter, 250 ms for sheet exit.
- Always honor `prefers-reduced-motion: reduce` — drop springs and
  cross-fades to instant or 80 ms linear.

### Iconography
- iOS: SF Symbols, multicolor or hierarchical as appropriate. Default
  weight regular, scale medium.
- Web: Lucide via a thin adapter in `apps/web/src/components/icon.tsx`
  (planned). Map each SF Symbol we use to its Lucide equivalent so a
  rename in one place updates both surfaces.

### Density rules
- **Workout logging:** dense. Min tap target 44 pt on iOS, 40 px on
  web. Set rows should fit 4–5 per viewport on a phone.
- **Analytics & insights:** breathes. Generous whitespace. Numbers are
  the hero — stat tiles get 28–34 pt type.
- **Forms / settings:** iOS grouped list pattern on iOS, web mirrors
  with cards of `--color-surface` separated by 16 px gaps.

### Component vocabulary
The implemented primitives live under `apps/web/src/components/`: `ui/`
(button, card, input, sheet, stat-tile, toast) plus feature folders
(`workouts/`, `programs/`, `charts/`, `layout/`, `auth/`, `nutrition/`).
All are flat and hairline-bordered per the editorial system: cards have
no drop shadow, segmented controls are underline tabs (not pills), chips
are outline and text-forward, the primary button is a clay fill and the
secondary is an outline that inverts to ink.

Browse the directory for the current set rather than trusting a list
here. If you need a primitive that isn't there, propose it before
painting it into a screen; it's likely intentionally missing.

---

## 4. What is built vs what needs designing

### Web — shipped (editorial)
Every route below is ported to the editorial design system and is
functional against the API. Remaining work is polish and edge states,
not first-time design.

| Route | State |
|---|---|
| `(auth)/sign-in` | Editorial. Apple (ink) + Google (outline). |
| `(app)/page.tsx` (today) | Editorial. Readiness, nutrition strip, workout hero, recs. |
| `(app)/workouts/` (list, active, summary) | Editorial. |
| `(app)/workouts/calendar/` | Editorial month grid. |
| `(app)/programs/` (overview, library, builder, templates, per-day) | Editorial, Direction A. |
| `(app)/exercises/[id]/` | Editorial. Trends / Sets / Variants / Notes. |
| `(app)/nutrition/` | Editorial, Direction A (log-first). |
| `(app)/analytics/` | Editorial. Volume heat, insights, trends. |
| `(app)/settings/` | Editorial. Appearance, units, integrations. |

### iOS — shipped as a visual port
All tabs (Today, Workouts, Programs, Nutrition, Insights, Settings) plus
the deep screens (active session, exercise detail, summary) are built in
SwiftUI against the editorial design system. They render against local
sample data; wiring them to the API is the open work, not visual design.

### Where design effort still helps most
1. **Polish and edge states** across the shipped surfaces: empty,
   loading, offline, and error states per section 9.
2. **iOS data states**: how each screen looks with real, partial, or
   failed data once the API layer lands.
3. **Cross-theme verification**: every screen in light and dark, with
   charts legible on both.

---

## 5. Key data shapes you will design around

Numbers and enums lifted from `tasks/00-overview/data-model.md` and
the API. Use them as the source of truth for any UI that filters,
groups, or labels by these dimensions.

### Identity & units
- All weights stored in **kg**. UI converts based on the user's unit
  preference (kg or lb). Tabular numerics, one decimal place for lb
  conversions, integer for kg unless trailing 0.5.
- All distances stored in **meters**. UI converts to km or mi.
- All durations stored in **seconds**. UI shows `mm:ss` for under an
  hour, `h:mm` for over.
- IDs are UUID v7. Never show in the UI. Use exercise names, program
  names, dates.

### Sets
- `tracking_type`: `weight_reps`, `bodyweight_reps`, `weighted_bodyweight_reps`,
  `time`, `distance_time`, `reps_only`. Each variant changes the
  set-row layout — see `set-row.tsx`.
- `set_type`: `normal`, `warmup`, `drop`, `failure`, `amrap`, `top`,
  `backoff`. Show with a small label chip at the leading edge of the
  set row. Color: secondary text, not accent.

### Programs
- `program_goal`: `strength`, `hypertrophy`, `endurance`, `general`,
  `cut`. Affects suggested rep ranges and rest timer defaults.
- `progression_strategy`: `linear`, `double_progression`, `wave`,
  `rpe_based`, `manual`. Show as a small subtitle on the program card.
- `movement_pattern`: `squat`, `hinge`, `horizontal_push`,
  `horizontal_pull`, `vertical_push`, `vertical_pull`, `lunge`,
  `carry`, `core`, `isolation`. Used for the volume heat panel.

### Muscles (19 entries)
chest, lats, mid_back, lower_back, traps, rear_delts, side_delts,
front_delts, biceps, triceps, forearms, abs, obliques, glutes,
quads, hamstrings, adductors, abductors, calves.

The volume heat panel needs a visual for all 19 with a 4-level
saturation scale per week. Color: `--color-accent` at varying alpha.

### Recommendations (insights)
Returned by `GET /v1/recommendations`. Each has:
- `kind`: `add_weight`, `add_reps`, `reduce_weight`, `extra_rest`,
  `deload_week`, `swap_exercise`, `add_volume`, `cut_volume`.
- `confidence`: `low` | `medium` | `high`. Render with three pip dots.
- `rationale`: short string (≤ 60 chars). Plain text.
- A deep-link target (`exercise_id`, `program_id`, or `session_id`).

Render as cards. High confidence is the only one that gets a primary
CTA; low/medium get secondary text "Tap to learn why".

### Readiness
Comes from Fitbit daily metrics. Three bands:
- `low` (0–39): `--color-destructive`. Tile copy: "Take it easy".
- `moderate` (40–69): `--color-warning`. Tile copy: "Workable".
- `high` (70–100): `--color-success`. Tile copy: "Push it".

The numeric score (0–100) is the hero on the tile. Subtitle is the
band copy. The band determines the dot color, not the number color —
the number stays `--color-text` so it's always readable.

### Nutrition
- Meals are flexible, not fixed slots. In flexible mode they are
  free-form ("Meal 1..n"); in plan mode they come from the active meal
  plan's slots. The `meal_type` field still exists in the data but is no
  longer surfaced as fixed breakfast/lunch/dinner/snack sections.
- `food_source`: `manual`, `barcode`, `usda` (FatSecret-backed search).
  Source decides the small leading icon on the meal item. There is no
  photo source; photo recognition was dropped.
- The day leads with a slim calorie masthead plus a large quick-add
  search, not a macro ring. Protein, carbs, and fat are first-class on a
  P/C/F strip.

### Analytics insights
`GET /v1/insights/weekly` returns 3–6 cards a week. Each has:
- `kind`: `volume_change`, `pr_streak`, `plateau`, `imbalance`,
  `under_recovered`, `over_reaching`, `consistency`.
- `severity`: `info` | `notice` | `warning`. Maps to border color
  (`--color-border`, `--color-warning`, `--color-destructive`).
- `body`: 1–2 sentences. Render as-is — do not parse markdown in
  insights.

---

## 6. Suggested screen list (start with these)

### iOS — Tab 1: Today
- Large date header ("Tuesday, 26 May").
- Readiness tile (full-bleed card, 1 row, score + band).
- Scheduled workout card if any (program day name, exercise count,
  estimated duration). Primary CTA "Start".
- Recommendation carousel (3 cards max).
- Quick-log meal CTA (compact, secondary).

### iOS — Tab 2: Workouts
- Calendar strip at top (7 days, swipeable).
- "Today" section: scheduled or active session.
- "This week" section: completed sessions.
- "Browse history" link to full history view.

### iOS — Tab 3: Nutrition
- Slim calorie masthead + P/C/F strip at top, then a quick-add search.
- Meals are flexible (free-form) or driven by the active meal plan's
  slots; no fixed breakfast/lunch/dinner sections.
- Each meal: items list + an add CTA.
- Bottom sheet for adding: tabs `Search` / `Scan` (no photo tab).

### iOS — Tab 4: Insights (Analytics)
- Volume heat panel (this week vs last 4).
- Per-exercise trends (tap-through to exercise page).
- Weekly insights cards.

### iOS — Tab 5: Settings
- Profile (display name, accent color, unit system).
- Connections (Fitbit toggle + status).
- Programs (active program selector).
- About (version, sign out).

### Per-exercise page (deep-linked from many places)
- Sticky header: exercise name, primary muscle pills, equipment chip.
- Tabs: `Trends` / `Sets` / `Variants` / `Notes`.
- `Trends`: estimated 1RM chart, working set volume chart.
- `Sets`: paginated list of every set ever performed, grouped by date.
- `Variants`: same movement, different equipment / grip.
- `Notes`: free-text per-exercise notes.
- Floating "Add to today" or "Start session" CTA.

### Active workout (mid-session)
- Top: program day name + session timer.
- Per-exercise card: exercise name, target sets x reps, rest timer.
- Set rows: previous performance ghost, current input, RPE picker.
- Sticky bottom bar: current rest timer + finish button.
- Web: keyboard shortcuts already implemented (`apps/web/src/components/workouts/keyboard-shortcuts.tsx`)
  — design a shortcuts cheat sheet sheet for "?" key.

### Workout summary
- Big PR banner if any PRs happened.
- Volume by muscle for this session vs typical.
- Set-by-set table.
- Notes field.
- Recommendation cards for next session.

---

## 7. Constraints (these are hard requirements)

1. **Light + dark mode are both first-class.** No "designed for dark,
   light is fine-ish". Token-driven so flipping `prefers-color-scheme`
   produces an intentional UI on both sides.
2. **Reduce Motion.** Every spring and slide animation must have an
   instant or 80 ms-linear fallback.
3. **Dynamic Type.** iOS UI must reflow up to xxxLarge accessibility
   sizes. Web must respect the user's root font size (don't `font-size:
   16px !important` anywhere).
4. **Tabular numerics on every stat.** No "187" jumping to "188" with
   a different glyph width.
5. **44 pt minimum touch targets** on iOS. 40 px on web mobile.
6. **No skeleton-shimmer-everywhere.** Use TanStack Query's
   placeholderData where there's a sensible last-good value. Shimmer
   only for first-ever loads.
7. **Offline.** The workout logging path must work fully offline —
   logging a set should never block on network. Design needs an
   inline "synced" / "pending sync" indicator on completed sets.
8. **One-handed.** Critical actions during a workout (log set, start
   rest timer, finish session) must be reachable with a right thumb in
   the bottom 60% of the screen.
9. **No modal stacking deeper than two.** If you need three levels,
   redesign the flow.
10. **Errors never block the workout.** If something fails to sync,
    the set still saves locally and the UI shows a quiet badge — no
    full-screen error states mid-session.

---

## 8. User flows (happy paths)

### Sign in
1. Open app → unauthed → sign-in screen.
2. Tap Apple or Google → OS sheet → return with ID token.
3. App posts to `/v1/auth/exchange` → receives JWT + refresh.
4. Land on Today.

### Start a scheduled workout
1. Today screen shows "Push day A — 5 exercises, ~55 min".
2. Tap "Start". Navigate to active session (web: `/workouts/{id}`).
3. Log sets per exercise. Rest timer auto-starts after a logged set.
4. Tap "Finish". Go to summary. See PRs and recommendations.

### Create a program from a template
1. Programs tab → "New program" → choose template (e.g., 5/3/1, PPL,
   Upper/Lower).
2. Customize day names, exercise picks, schedule.
3. Activate. Today screen now shows next scheduled day.

### Log a meal via search or scan
1. Nutrition tab → quick-add search (or "+" → Scan for a barcode).
2. Pick a food from FatSecret-backed results or scan its barcode.
3. Adjust the serving; the macros fill in.
4. Save to a free-form meal or the active plan's slot.
5. The calorie masthead and P/C/F strip update.

### Connect Fitbit
1. Settings → Connections → Fitbit → Connect.
2. OAuth flow → redirect back to app.
3. First sync → readiness tile populates on Today within ~1 min.

### View an insight and adjust the program
1. Today or Insights tab → tap a "Plateau on bench" card.
2. Routes to per-exercise page for bench, Trends tab focused.
3. Card at top: "Try a deload week" — primary CTA "Apply to program".
4. Confirmation sheet → program updated.

---

## 9. Empty / loading / error states (please design these explicitly)

- Today with no scheduled workout: friendly "Rest day" with a small
  CTA "Browse programs" — not a giant empty illustration.
- Today before any data exists: "Welcome — start by picking a
  program template".
- Workouts calendar empty week: muted "Nothing logged this week".
- Nutrition with no logged meals today: ring at 0, "Tap + to log
  a meal".
- Analytics with under 2 weeks of data: stat tiles show "—" not
  zeros; one line of helper text "We'll show trends once you have
  two weeks of sessions".
- Offline indicator: small pill in the top bar, not a banner. Click
  shows pending-sync count.
- Sync error: per-set badge, never a modal during a session.
- Rate-limited (429): toast "Give that a minute" — not a destructive
  banner.
- Fitbit disconnected: readiness tile shows "—" with subtitle
  "Connect Fitbit" linking to settings.

---

## 10. What this brief does not decide

Open questions for you (Claude Design) to propose on:

- **Today screen layout.** Three reasonable layouts: hero readiness
  full-bleed + cards below; vertical split readiness + workout; or a
  stack with workout first if scheduled, readiness inline. Pick one,
  show why.
- **Volume heat panel.** Body diagram vs grid vs horizontal bar list
  per muscle. iOS Health uses body diagrams; that may be too literal.
- **Insights card density.** Single column full-width vs two-column
  on web. iOS will be single column either way.
- **Accent color application.** Should accent apply to the whole
  active-workout chrome, or stay limited to CTAs and selection?
- **Web sidebar vs top nav.** Sidebar is built — is that the right
  call for a personal app that mostly lives on iOS?
- **Calendar view.** Strip-of-days on a phone is the standard. On the
  web, full month grid or week stack?

---

## 11. Handoff format

When proposing screens, deliver:

1. **Static mockups** in both light and dark mode.
2. **Mobile + desktop** for the web, **iPhone 15-class** for iOS
   (390 x 844 pt safe area).
3. **Token references** — annotate which `--color-*` and
   `--radius-*` each element uses. New tokens require a proposal.
4. **Component reuse map** — which existing components in
   `apps/web/src/components/` you're using, and which need to be
   new. Justify any new primitive.
5. **Accessibility notes** — contrast ratios for every color pair,
   dynamic-type behavior at xLarge / xxLarge, Reduce-Motion fallback.

Avoid: Figma-style "auto-layout" markup, hex codes (use OKLCH or
token names), Lorem Ipsum (use realistic data from section 5).

---

## 12. Pointers to source-of-truth files

- `tasks/00-overview/design-system.md` — canonical design language.
- `tasks/00-overview/api-conventions.md` — API shape + error envelope.
- `tasks/00-overview/data-model.md` — entities and enums.
- `apps/web/src/styles/tokens.css` — implemented tokens.
- `apps/web/src/components/` — implemented component vocabulary.
- `packages/openapi/openapi.json` — generated, every endpoint and
  schema.
- `CURRENT-STATE.md` — what is built vs deferred at the repo level.

If anything in this brief conflicts with `tasks/00-overview/*.md`, the
spec under `tasks/` wins and this brief should be updated.
