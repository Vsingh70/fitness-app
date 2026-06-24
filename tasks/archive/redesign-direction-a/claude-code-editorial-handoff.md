# Editorial redesign — implementation guide for Claude Code

This document tells you (Claude Code, working in the `fitness-app` repo) how to
implement the **editorial** visual redesign in the real Next.js web app
(`apps/web`). A complete, interactive prototype of the target design already
exists — treat it as the **visual source of truth** and match it.

---

## 0. What "editorial" means here

A minimalist, magazine-like system. The pivot from the old look:

| Aspect | Before | After (editorial) |
|---|---|---|
| Palette | cool white + saturated system-blue | **warm paper + ink**, one muted **clay** accent |
| Surfaces | filled cards, soft drop-shadows, 12px radius | **flat**, hairline 1px rules, **no shadow**, 4px radius |
| Type | SF Pro + SF Pro Rounded numerals | **display serif** for titles & figures, sans for body, mono for labels |
| Semantic color | bright green/orange/red | **muted** sage / ochre / oxblood / mustard |
| Labels | sentence-case captions | **uppercase, letter-spaced kickers** |
| Controls | pill segmented, filled chips | **underline tabs**, **text-forward hairline chips** |
| Primary button | blue fill | clay fill (paper text); **secondary = outline** |

Restraint is the whole point: lots of whitespace, hairlines instead of boxes,
color used sparingly, typography doing the heavy lifting.

---

## 1. Source of truth (the prototype)

The prototype lives in the **design project** (HTML/CSS, framework-agnostic).
Open these and match them screen-for-screen. Token + shared CSS:

- `assets/tokens.css` — the editorial design tokens (OKLCH). **This is canonical.**
- `assets/app.css` — the editorial component styles (cards, buttons, chips, segmented, stat, sidebar, topbar, tables, lists).

Screen prototypes → repo routes/components:

| Prototype file | Repo route / component |
|---|---|
| `today.html` | `app/(app)/page.tsx` (Today) |
| `workouts.html` | `app/(app)/workouts/` |
| `workout-active.html` | active session UI + `components/workouts/*` |
| `workout-summary.html` | session summary view |
| `calendar.html` | `app/(app)/calendar/` |
| `programs.html`, `program-editor.html`, `program-template.html` | `app/(app)/programs/` |
| `exercise.html` | `app/(app)/exercises/` |
| `nutrition.html` | `app/(app)/nutrition/` |
| `analytics.html` | `app/(app)/analytics/` |
| `settings.html` | `app/(app)/settings/` |
| `sign-in.html` | `app/(auth)/sign-in/` + `components/auth/sign-in-buttons.tsx` |

When a detail is ambiguous, the prototype wins.

---

## 2. Tokens — `apps/web/src/styles/tokens.css`

Replace the token **values** with the editorial set below. Keep the existing
structure (`:root`, `@media (prefers-color-scheme: dark)`, `[data-theme="dark"]`,
`[data-accent="…"]`). Note three additions: `--font-serif`, `--color-*-soft`
helpers, and `--font-rounded` now **aliases the serif** (so every existing
`--font-rounded` / numeric reference becomes serif automatically).

```css
:root {
  /* Surfaces — warm paper */
  --color-bg: oklch(0.962 0.008 83);
  --color-surface: oklch(0.945 0.010 83);
  --color-surface-elevated: oklch(0.985 0.006 83);
  --color-surface-sunken: oklch(0.922 0.012 83);
  --color-border: oklch(0.28 0.012 64 / 0.16);
  --color-border-strong: oklch(0.28 0.012 64 / 0.30);
  --color-overlay: oklch(0.20 0.01 60 / 0.4);

  /* Text — warm ink */
  --color-text: oklch(0.255 0.013 58);
  --color-text-secondary: oklch(0.45 0.012 58);
  --color-text-tertiary: oklch(0.60 0.010 60);
  --color-text-inverse: oklch(0.97 0.008 83);

  /* Accent — clay */
  --color-accent: oklch(0.545 0.108 48);
  --color-accent-soft: oklch(0.545 0.108 48 / 0.11);
  --color-accent-foreground: oklch(0.975 0.008 83);

  /* Semantic — muted */
  --color-success: oklch(0.54 0.062 140);     --color-success-soft: oklch(0.54 0.062 140 / 0.14);
  --color-warning: oklch(0.62 0.090 74);      --color-warning-soft: oklch(0.62 0.090 74 / 0.14);
  --color-destructive: oklch(0.49 0.130 32);  --color-destructive-soft: oklch(0.49 0.130 32 / 0.13);
  --color-pr: oklch(0.66 0.092 78);           --color-pr-soft: oklch(0.66 0.092 78 / 0.18);

  /* Radii — restrained */
  --radius-card: 4px;
  --radius-button: 7px;
  --radius-sheet: 14px;

  /* Type */
  --font-serif: "Iowan Old Style", "Palatino Linotype", Palatino, "New York", Georgia, "Times New Roman", serif;
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  --font-numeric: var(--font-serif);   /* tabular figures render serif */
  --font-rounded: var(--font-serif);   /* legacy alias */
}
```

Dark mode (`@media prefers-color-scheme: dark` **and** `[data-theme="dark"]` — keep both in sync):

```css
  --color-bg: oklch(0.165 0.007 68);
  --color-surface: oklch(0.205 0.008 68);
  --color-surface-elevated: oklch(0.225 0.008 68);
  --color-surface-sunken: oklch(0.135 0.006 68);
  --color-border: oklch(0.86 0.02 82 / 0.14);
  --color-border-strong: oklch(0.86 0.02 82 / 0.26);
  --color-text: oklch(0.93 0.012 83);
  --color-text-secondary: oklch(0.72 0.012 83);
  --color-text-tertiary: oklch(0.55 0.010 80);
  --color-accent: oklch(0.66 0.110 50);   --color-accent-soft: oklch(0.66 0.110 50 / 0.20);
  --color-success: oklch(0.66 0.062 140);
  --color-warning: oklch(0.72 0.090 74);
  --color-destructive: oklch(0.60 0.140 32);
  --color-pr: oklch(0.76 0.098 80);
```

Accent variants — keep the 5 keys (`blue/indigo/mint/orange/pink`) so the
existing accent-picker + `data-accent` plumbing keeps working, but recolor to
the muted editorial hues. (Relabel the UI names to **Clay / Slate / Teal /
Ochre / Rose** — see §4 settings.)

```css
[data-accent="blue"]   { --color-accent: oklch(0.545 0.108 48);  --color-accent-soft: oklch(0.545 0.108 48 / 0.11); }  /* Clay (default) */
[data-accent="indigo"] { --color-accent: oklch(0.480 0.052 264); --color-accent-soft: oklch(0.480 0.052 264 / 0.13); } /* Slate */
[data-accent="mint"]   { --color-accent: oklch(0.520 0.058 196); --color-accent-soft: oklch(0.520 0.058 196 / 0.13); } /* Teal */
[data-accent="orange"] { --color-accent: oklch(0.605 0.092 72);  --color-accent-soft: oklch(0.605 0.092 72 / 0.13); }  /* Ochre */
[data-accent="pink"]   { --color-accent: oklch(0.520 0.094 12);  --color-accent-soft: oklch(0.520 0.094 12 / 0.13); }  /* Rose */
```
(Provide dark-mode lifted versions too, mirroring the existing file.)

The full canonical file is `assets/tokens.css` in the design project — copy it verbatim if you have access.

---

## 3. Theme wiring — `apps/web/src/app/globals.css`

The app uses **Tailwind v4 CSS-first** (`@theme`). Update it so the new tokens
and serif are available as utilities:

```css
@theme {
  /* …existing color mappings stay… add the soft + serif tokens: */
  --color-accent-soft: var(--color-accent-soft);
  --color-success-soft: var(--color-success-soft);
  --color-warning-soft: var(--color-warning-soft);
  --color-destructive-soft: var(--color-destructive-soft);
  --color-pr: var(--color-pr);
  --color-pr-soft: var(--color-pr-soft);

  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  --font-serif: "Iowan Old Style", "Palatino Linotype", Palatino, "New York", Georgia, serif;
  --font-numeric: var(--font-serif);

  --radius-card: 4px;     /* was 12px */
  --radius-button: 7px;   /* was 10px */
  --radius-sheet: 14px;
}
```

This gives you `font-serif`, `bg-accent-soft`, `text-pr`, etc. The existing
`.tabular-nums` helper already points at `--font-numeric`, so **all tabular
figures become serif** for free.

Add a base rule so display headings default to serif:

```css
@layer base {
  h1, h2, .display { font-family: var(--font-serif); font-weight: 500; letter-spacing: -0.015em; }
}
```

> Fonts: the stack uses the system serif ("Iowan Old Style"/Palatino/Georgia) —
> zero web-font cost and a genuinely editorial feel. If you want a branded serif
> later, load one via `next/font` (e.g. *Spectral* or *Source Serif 4*) and swap
> `--font-serif`. Do **not** use Inter/Roboto for display.

---

## 4. Component changes

All components are token-driven Tailwind, so most of the work is done by §2–§3.
The deltas below are the ones the token swap does **not** cover. Match the
prototype's `assets/app.css` for exact spacing.

**`components/ui/card.tsx`** — remove the drop shadow; flat + hairline only.
```diff
- "border-border bg-surface-elevated rounded-[var(--radius-card)] border",
- "shadow-[0_1px_2px_rgba(0,0,0,0.04)]",
+ "border-border bg-surface-elevated rounded-[var(--radius-card)] border",
```
Section/card headers: make titles uppercase tracked labels
(`text-xs font-semibold uppercase tracking-[0.12em] text-text-secondary`),
not bold sentence case.

**`components/ui/button.tsx`** — primary keeps `bg-accent text-accent-foreground`.
Change **secondary** to an outline that inverts on hover; bump font-weight to 600:
```diff
- secondary: "bg-surface text-text border border-border hover:bg-surface-elevated",
+ secondary: "bg-transparent text-text border border-text hover:bg-text hover:text-bg",
```
Sizes: `md` → `h-10`, primary actions in the prototype use `h-[42px]`/`lg`. Radius now 7px via token.

**`components/ui/stat-tile.tsx`** — figure goes serif & larger; label becomes a
kicker; drop the filled box for a top-rule (optional but matches prototype):
```diff
- "border-border bg-surface-elevated flex flex-col gap-1 rounded-[var(--radius-card)] border p-4",
+ "flex flex-col gap-1.5 border-t border-border-strong pt-4",
...
- <span className="text-text-secondary text-sm">{label}</span>
+ <span className="text-text-secondary text-[10px] font-semibold uppercase tracking-[0.12em]">{label}</span>
- <span className="text-text text-3xl font-semibold tabular-nums">{value}</span>
+ <span className="text-text font-serif text-3xl font-medium tabular-nums tracking-tight">{value}</span>
```

**`components/ui/input.tsx`** — border `border-border-strong`, focus ring
`focus:ring-[3px] focus:ring-accent-soft focus:border-accent`, radius 7px.
Numeric inputs: `font-serif tabular-nums text-right`.

**`components/ui/sheet.tsx`** — `rounded-[var(--radius-sheet)]`, add a grabber
(`h-1.5 w-9 rounded-full bg-text-tertiary mx-auto`), flat surface.

**`components/ui/toast.tsx`** — flat: hairline border, no heavy shadow.

**`components/layout/desktop-sidebar.tsx`** — brand goes serif; active item uses
an **inset left rule** instead of a tinted blue fill:
```diff
- <span className="text-lg font-semibold tracking-tight">Gym</span>
+ <span className="font-serif text-xl font-medium tracking-tight">gym</span>
...
- active ? "bg-accent/10 text-accent"
-        : "text-text-secondary hover:bg-surface-elevated hover:text-text",
+ active ? "bg-surface-elevated text-text font-semibold shadow-[inset_2px_0_0_var(--color-accent)]"
+        : "text-text-secondary hover:bg-surface-elevated hover:text-text",
```

**`components/layout/top-bar.tsx`** — page title `font-serif text-xl font-medium`;
breadcrumb `text-[11px] uppercase tracking-[0.14em] text-text-tertiary`.

**`components/layout/mobile-tabbar.tsx`** — labels `uppercase tracking-[0.06em] text-[9px]`; active is `text-text` (ink), not accent.

**Segmented / tabs (wherever rendered)** — convert from filled pills to
**underline tabs**: container `flex gap-[18px] border-b border-border`; each tab
`pb-[7px] -mb-px border-b-[1.5px] border-transparent uppercase tracking-[0.08em] text-xs font-semibold text-text-secondary`; active adds `border-text text-text`.

**Chips / badges** — text-forward hairline pills: `inline-flex h-[22px] items-center
rounded-full border border-border-strong px-[9px] text-[10px] font-semibold
uppercase tracking-[0.1em]`, transparent background. Variant = colored text +
matching `border-{tone}/45`. PR uses `text-pr`.

**`components/workouts/set-row.tsx`** — keep the grid. PR row: `bg-pr/10` is fine
(subtle). Add a "current set" state `bg-accent-soft`; completed `bg-success-soft`
with the figure in `text-success`. Field inputs `font-serif`. The "x" delete
should be an icon, not a literal `x`.

**`components/workouts/rest-timer.tsx` + `session-sticky-bar.tsx`** — flat
surface `bg-surface-elevated border border-border` (drop heavy shadow; a single
soft `shadow-[var(--shadow-3)]`-equivalent is OK for the floating bar only); the
countdown ring uses `var(--color-accent)`; figures serif.

**`components/charts/trend-chart.tsx`** (recharts) — already token-driven. Just:
- line `strokeWidth={2}` → `1.6`; keep `stroke={ACCENT}` (now clay).
- overlay/PR series use `var(--color-pr)` (mustard), dashed.
- bars: `fill={ACCENT}`, `radius={[3,3,0,0]}`.
- grid already hairline — keep `strokeDasharray="2 4"`, `vertical={false}`.
- the muscle-volume heatmap (analytics) uses the accent ramp: tints at
  `color-mix(in oklab, var(--color-accent) {16,34,62}% , transparent)` then solid accent for the top bucket. See `analytics.html`.

**`components/programs/volume-summary.tsx`** — bars `bg-accent`; under-target
bars `bg-warning`; target marker = 2px `bg-text-tertiary` tick.

**`components/auth/sign-in-buttons.tsx` + sign-in page** — title goes serif &
larger; Apple button is **ink** (`bg-text text-bg`), Google button is outline
(`border border-border bg-surface-elevated`). See `sign-in.html`.

---

## 5. Typography rules (apply everywhere)

- **Display serif** (`font-serif`): page titles (`h1/h2`), card/section headlines,
  hero numbers, every stat figure (covered via `--font-numeric`).
- **Sans** (`font-sans`): body copy, buttons, table cells, form fields.
- **Mono** (`font-mono`) or tracked sans: tiny labels/kickers — uppercase,
  `tracking-[0.1em]–[0.16em]`, `text-text-secondary`.
- Tabular numerals everywhere numbers appear (`tabular-nums`).
- Don't bold the serif past `font-medium` (500); editorial serif reads lighter.

---

## 6. Acceptance checklist

- [ ] No drop shadows anywhere except the one floating rest-timer bar.
- [ ] Background is warm paper (light) / warm near-black (dark) — never pure #fff/#000 cool.
- [ ] All titles & every number render in the serif.
- [ ] Cards are hairline-bordered, 4px radius, no fill jump from the page.
- [ ] Segmented controls are underline tabs, not pills.
- [ ] Chips are outline/text, not solid color fills.
- [ ] Primary buttons clay; secondary buttons outline-invert.
- [ ] Sidebar active item = inset clay rule + ink text (no blue wash).
- [ ] Accent picker still works; labels read Clay/Slate/Teal/Ochre/Rose.
- [ ] Dark mode verified on every route; charts legible on both themes.
- [ ] Diff the result against the matching `*.html` prototype at 1280px and at mobile width.

## 7. Out of scope / keep as-is

- All behavior, data fetching, routing, offline queue, auth, keyboard shortcuts.
- Component **APIs** (props) — only class strings / tokens change.
- Accessibility: keep focus-visible rings (now `outline-accent`), hit targets ≥44px, contrast AA.
