# Editorial design system — iOS implementation guide for Claude Code

How to implement the **editorial** look in the SwiftUI iOS app
(`apps/ios`). The Xcode project itself is scaffolded by
`tasks/08-ios/01-ios-skeleton.md` — **apply this guide once that skeleton
exists.** Until then, treat this as the design spec the skeleton should adopt.

The **visual source of truth** is the prototype in the design project:
`ios.html` (a canvas of all iPhone frames) backed by `ios/styles.css`,
`ios/components.jsx`, `ios/screens-tabs-1.jsx`, `ios/screens-tabs-2.jsx`,
`ios/screens-deep.jsx`. Match those screen-for-screen. The web app shares the
same system — see `claude-code-editorial-handoff.md` for the web side; keep the
two visually in sync (the web "mirrors" iOS per the design brief).

---

## 0. The aesthetic

Minimalist, magazine-like. Warm **paper + ink**, one muted **clay** accent, a
**display serif** (iOS *New York*, i.e. `.serif` design) for titles & every
figure, sans for body, hairline rules instead of filled cards, **no shadows**
(except one floating rest-timer bar), uppercase letter-spaced kickers, muted
semantic tones (sage / ochre / oxblood / mustard). Color is used sparingly;
typography carries the design.

---

## 1. Color — Asset Catalog (`Assets.xcassets`)

Create a **Color Set** per token below, each with **Any (light)** and **Dark**
appearances. Values are the exact hexes from the prototype (`ios/styles.css`).
Use sRGB. Reference via an `extension Color` (don't hardcode hex in views).

| Color Set | Light | Dark | Role |
|---|---|---|---|
| `BG` | `#F3F0E8` | `#15120E` | app background (warm paper / near-black) |
| `Surface` | `#FBF9F3` | `#1E1A15` | raised paper / grouped row bg |
| `Surface2` | `#FFFFFF` | `#221E18` | elevated |
| `Label` | `#211D17` | `#EFE9DD` | primary ink |
| `Label2` | `#211D17` @ 56% | `#EFE9DD` @ 56% | secondary |
| `Label3` | `#211D17` @ 32% | `#EFE9DD` @ 32% | tertiary |
| `Separator` | `#211D17` @ 14% | `#EFE9DD` @ 14% | hairline rules |
| `Fill` | `#211D17` @ 5% | `#EFE9DD` @ 6% | faint fill |
| `Accent` (clay) | `#9D5635` | `#C67E5A` | the one accent |
| `Success` (sage) | `#5E6B4F` | `#8C9576` | up/positive |
| `Warning` (ochre)| `#B07B3C` | `#C9974F` | caution |
| `Destructive` (oxblood) | `#8C3A2E` | `#C0604E` | delete/error |
| `PR` (mustard) | `#A8842F` | `#C9A24F` | personal-record highlight |

Set **AccentColor** to clay. The user-selectable accent (Clay / Slate / Teal /
Ochre / Rose) maps to a stored enum → swap the `Accent` color at runtime via an
environment value; defaults to Clay. Muted hex set:
Clay `#9D5635`, Slate `#4C4A57`, Teal `#4F6B63`, Ochre `#B07B3C`, Rose `#99506A`
(lifted ~12% L for dark).

```swift
extension Color {
    static let bg = Color("BG")
    static let surface = Color("Surface")
    static let surface2 = Color("Surface2")
    static let ink = Color("Label")
    static let ink2 = Color("Label2")
    static let ink3 = Color("Label3")
    static let hairline = Color("Separator")
    static let fill = Color("Fill")
    static let accent = Color("Accent")
    static let success = Color("Success")
    static let warning = Color("Warning")
    static let destructive = Color("Destructive")
    static let pr = Color("PR")
}
```

---

## 2. Typography

iOS ships *New York* as the system serif — use `design: .serif`. Body/labels
stay on SF (`.default`). Define a small `Typography` enum:

```swift
extension Font {
    // Display serif — titles & figures
    static let largeTitleSerif = Font.system(size: 34, weight: .medium, design: .serif)
    static let titleSerif      = Font.system(size: 24, weight: .medium, design: .serif)
    static let figure          = Font.system(size: 30, weight: .medium, design: .serif) // stat numbers
    static let figureSmall     = Font.system(size: 18, weight: .medium, design: .serif)
    // Body / UI — sans
    static let headline        = Font.system(size: 16, weight: .semibold)
    static let body            = Font.system(size: 16)
    static let footnote        = Font.system(size: 13)
    static let caption         = Font.system(size: 12)
}
```

**Kicker** modifier (uppercase, tracked, secondary) — used everywhere for
section labels / metadata:

```swift
struct Kicker: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(size: 11, weight: .semibold))
            .textCase(.uppercase)
            .tracking(1.6)
            .foregroundStyle(Color.ink2)
    }
}
extension View { func kicker() -> some View { modifier(Kicker()) } }
```

Rules:
- Screen titles, card headlines, hero copy, **all numbers/stats** → serif.
- Every numeric uses `.monospacedDigit()` (tabular).
- Body text, buttons, table cells, form fields → sans.
- Tiny labels/metadata → `.kicker()`.
- Don't exceed `.medium` weight on the serif.

---

## 3. Components

Match `ios/styles.css`. Key specs:

**Card** — flat: `Color.surface2` (or transparent on paper), `cornerRadius 4`,
`1pt` `Color.hairline` border, **no shadow**. Prefer dividing content with
hairlines + whitespace over nesting filled cards.
```swift
struct EditorialCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content.padding(16)
            .background(Color.surface2)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.hairline, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }
}
```

**Grouped list** — transparent rows, full-width 1pt hairline dividers (not
inset), no chunky icon tiles: use a thin monochrome SF Symbol in `Color.ink`,
**not** a colored rounded-rect. `List` → set `.listStyle(.plain)`,
`.listRowSeparatorTint(.hairline)`, `.scrollContentBackground(.hidden)`,
background `Color.bg`.

**Tab bar** — 5 tabs (Today, Workouts, Nutrition, Insights, Settings). Selected
tint = `Color.ink` (not accent), unselected `Color.ink3`; labels are tiny
uppercase. `UITabBar` appearance: transparent + hairline top via
`UITabBarAppearance` (configureWithTransparentBackground + thin blur).

**Primary button** — ink fill, paper label, `cornerRadius 7`, height 50:
```swift
.background(Color.ink).foregroundStyle(Color.bg)
```
**Secondary** — transparent, `1pt Color.ink` border, ink label (inverts on press).

**Segmented control** — do **not** use `Picker(.segmented)` (it's a filled
pill). Build **underline tabs**: an HStack of buttons, each uppercase/tracked
12pt; selected gets a 1.5pt `Color.ink` underline; row sits on a `Color.hairline`
bottom rule.

**Toggle** — `.tint(Color.ink)` so "on" reads ink, not green.

**Chip / badge** — text-forward: capsule with `1pt` tone-colored border,
transparent fill, 10pt uppercase tracked, colored text. PR chip uses `Color.pr`.

**Stat tile** — top hairline rule, kicker label, big serif `.figure` value with
sans unit, optional muted delta (sage up / oxblood down).

**Rings** — thin strokes (`lineWidth 3–8`), `Color.accent` track at low opacity.
Nutrition uses a 3-ring stack (clay/sage/ochre at reduced chroma). Use
`Circle().trim(from:to:).stroke(style: .init(lineWidth:, lineCap: .round))`.

**Charts** — Swift Charts (`import Charts`). `LineMark` `Color.accent`,
`lineWidth 1.6`; PR/overlay series `Color.pr` dashed; `BarMark` `Color.accent`
with `cornerRadius 3`; gridlines `Color.hairline` dashed, hide vertical;
axis labels in mono caption `Color.ink3`. Muscle-volume heatmap = accent ramp
(`Color.accent.opacity(0.16 / 0.34 / 0.62)` then solid).

**Active workout** — set rows: current `Color.accent.opacity(0.10)`, completed
`Color.fill` with the figure in `Color.success`; serif figures; checkmark fills
`Color.success`. Plate-math chips use ink/`Label2`, not red. Rest bar floats:
`Color.surface2`, hairline border, `cornerRadius 14`, single soft shadow OK.

**Sign-in** — serif title; Apple button **ink** (`Color.ink`/paper), Google
button outline (`Color.surface2` + hairline). Match `sign-in.html`.

---

## 4. Screen mapping (prototype → SwiftUI view)

| Prototype (in `ios.html`) | SwiftUI view |
|---|---|
| Today | `TodayView` (Fitbit metric carousel, nutrition strip, scheduled-workout feature block, recs, weekly stats) |
| Workouts | `WorkoutsView` (week strip, scheduled, history list) |
| Nutrition | `NutritionView` (3-ring + macro bars, meal sections, add-meal sheet) |
| Insights | `InsightsView` (stat grid, volume heat, tonnage chart, insight cards, progress-photo compare) |
| Settings | `SettingsView` (profile, appearance + accent picker, units, training, connections, data) |
| Active workout | `ActiveSessionView` (exercise rail, set rows, plate math, floating rest bar) |
| Per-exercise | `ExerciseDetailView` (PR tiles, rec strip, underline tabs: Trends/Sets/Variants/Notes, e1RM + volume charts) |
| Workout summary | `SessionSummaryView` (PR feature block, stat tiles, volume bars, set list, next-session recs) |

Same mock user across screens: **Alex Chen**, week 4 of 8, PPL — Vanilla 6-day.

---

## 5. Acceptance checklist

- [ ] App background warm paper (light) / warm near-black (dark) — never pure white/black.
- [ ] Every title and every number renders in *New York* (`.serif`); numbers are monospaced-digit.
- [ ] No drop shadows except the floating rest-timer bar.
- [ ] Cards = hairline-bordered, 4pt radius, flat.
- [ ] Lists use full-width hairline separators; no colored icon tiles.
- [ ] Segmented controls are underline tabs, not filled pills.
- [ ] Toggles tint ink; tab bar selected tint ink.
- [ ] Chips are outline/text, not solid fills.
- [ ] Primary buttons ink; secondary outline-invert; Apple sign-in ink.
- [ ] Accent picker swaps Clay/Slate/Teal/Ochre/Rose live; Dynamic Type & dark mode verified.
- [ ] Side-by-side against each frame in `ios.html`.

## 6. Out of scope

- Networking, auth (OIDC), HealthKit/Fitbit sync, offline queue, persistence — behavior unchanged; this guide is **visual system only**.
- Don't introduce third-party UI frameworks; native SwiftUI + Swift Charts only.
```
```
> Pairs with `claude-code-editorial-handoff.md` (web). Tokens are intentionally
> identical in meaning across both so the two apps stay in lockstep.
