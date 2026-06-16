# Design system

Editorial: warm paper and ink, one restrained clay accent, a display serif doing the heavy lifting. iOS-native feel everywhere; the web mirrors the iOS app, and the iOS app is the source of truth for visual decisions.

This file is canonical. The implemented tokens follow it: `apps/web/src/styles/tokens.css` on web and `apps/ios/GymApp/Core/Design/` on iOS. The per-surface porting notes live in `tasks/redesign/claude-code-editorial-handoff.md` (web) and `tasks/redesign/claude-code-editorial-ios.md` (iOS).

## Tone

- Minimalist and magazine-like. Lots of whitespace, hairlines instead of boxes, color used sparingly, typography carrying the page.
- Numbers are the hero. Weights, reps, kcal, percentages render in the serif at display sizes with tabular figures.
- Quiet and confident. No exclamation points, no emoji, no gym-bro maximalism.

## Color

Warm paper and ink, defined once per platform in OKLCH (`apps/web/src/styles/tokens.css`, `apps/ios/GymApp/Core/Design/Color+Editorial.swift`). Light is the default; dark is a warm near-black, never a cool grey. Reference semantic tokens, never raw OKLCH or hex.

- Background: warm paper. Surface, surface-elevated, and surface-sunken step around it by a few percent lightness, not by shadow.
- Borders: hairlines at low alpha (`--color-border`, `--color-border-strong`). Surfaces are separated by 1px rules, not fills or drop shadows.
- Text: warm ink (`--color-text`) plus two muted steps (secondary, tertiary) and an inverse for text on the accent.
- Accent: a single restrained clay (`--color-accent`), with an 11 percent `--color-accent-soft` tint for fills and focus rings. Default for everyone.
- Accent picker: five muted options labeled Clay (default), Slate, Teal, Ochre, Rose. The underlying data-accent keys stay blue/indigo/mint/orange/pink so the picker plumbing is unchanged; only the hues and labels are editorial.
- Semantic, all muted: success is sage, warning is ochre, destructive is oxblood, PR is mustard. Each has a soft variant for backgrounds.
- Volume heatmap: a five-step accent-tinted ink ramp (`--heat-0` through `--heat-4`).

## Typography

The editorial signature. A display serif sets titles and every figure; a system sans carries body; a mono sets tiny labels.

- Serif (`--font-serif`): page and section titles, hero numbers, and every stat figure (numerics route through the serif via `--font-numeric` and the legacy `--font-rounded` alias). The web loads a branded Source Serif 4 through next/font and falls back to a system serif stack (Iowan Old Style, Palatino, New York, Georgia). iOS uses the New York system serif (`.serif` design).
- Sans (`--font-sans`): body copy, buttons, table cells, form fields. SF Pro Text or system sans.
- Mono or tracked sans (`--font-mono`): kicker labels. Uppercase, letter-spaced (0.10em to 0.16em), secondary text color.
- Tabular numerics everywhere numbers appear, so figures line up.
- Do not bold the serif past medium (500); the editorial serif reads lighter.
- Scale matches iOS Dynamic Type. Base 17pt body, headlines 22/28/34.

## Components

Shared vocabulary (different code, same names). Flat and hairline-bordered by default.

- `Card`: flat surface, hairline 1px border, 4px radius, no drop shadow. Section and card headers are uppercase tracked kicker labels, not bold sentence case.
- `StatTile`: a serif figure over a top-rule, with an uppercase kicker label. The number is the hero.
- `SetRow`: one set entry, weight by reps by optional RPE, figures in the serif. The current set tints `--color-accent-soft`; a completed set tints `--color-success-soft`.
- `Segmented` and tabs: underline tabs, not filled pills. A bottom hairline with the active tab carrying an ink underline.
- `Chip` and badge: text-forward hairline pills, transparent background, uppercase tracked label. Colored variants tint the text and border, not a fill.
- `Button`: primary is a clay fill with paper text; secondary is an outline that inverts to ink on hover. 7px radius.
- `Input`: strong hairline border, a 3px `--color-accent-soft` focus ring; numeric inputs are serif, tabular, right-aligned.
- `Sheet`: bottom sheet on iOS, modal or side panel on web; flat surface, 14px top radius, grabber handle.
- `RestTimer`: flat surface with a hairline border; the countdown ring uses the accent; figures serif. The floating rest-timer bar is the one place a soft shadow is allowed.
- `Toast`: flat, hairline border, no heavy shadow. Top on iOS, top-right on web.
- Sidebar (web): serif brand; the active nav item is an inset clay left-rule plus ink text, not a tinted accent fill.

## Iconography

- SF Symbols on iOS, regular weight, medium scale.
- Web: Lucide via a thin adapter, mapped to the SF Symbol names so both surfaces read the same in docs.

## Motion

- Spring `cubic-bezier(0.32, 0.72, 0, 1)`: 120ms fast, 200ms base, 400ms for sheet enter.
- Reserve motion for navigation and the rest timer. Avoid bouncy animation on data updates.
- Honor Reduce Motion everywhere: drop springs and cross-fades to instant or an 80ms linear fallback.

## Surfaces and elevation

- Near-flat. `--shadow-1` is none; editorial leans on hairlines, not elevation. A faint `--shadow-2` and a real `--shadow-3` exist only for genuinely floating elements (the rest-timer bar, popovers).
- No drop shadows on cards. Surfaces read through the 1px rule and the small lightness step.

## Density

- Workout logging is high-density. Fit four to five set rows per phone viewport. Minimum tap target 44pt on iOS, 40px on web.
- Analytics and insights breathe. Generous whitespace, the serif figures at 28 to 34 pt.
- Forms and settings use the iOS grouped-list pattern; web mirrors with hairline-separated cards.

## Cross-platform parity

iOS first. When iOS and web disagree, iOS wins and web mirrors it, even if that means importing an iOS idiom (sheets, large titles, underline segmented controls). Where they must diverge: input (keyboard shortcuts on web, haptics on iOS) and navigation chrome (sidebar plus tab bar on web, tab bar plus nav stack on iOS). Do not invent web-only patterns that would not translate to iOS.
