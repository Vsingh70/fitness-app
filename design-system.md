# Design system

iOS-native feel everywhere. The web mirrors what the iOS app looks like; the iOS app is the source of truth for visual decisions.

## Tone

- Clean, calm, dense where it needs to be, generous where it doesn't.
- Inspired by Apple Fitness, Strong app, and the system Health app. Not gym-bro maximalism. Not editorial whitespace either.
- Numbers are the hero. Weights, reps, kcal, percentages. Use SF Pro Rounded for stat displays.

## Color

Tokens (defined once in `apps/web/src/styles/tokens.css` and `App/Resources/Colors.xcassets`):

- Background: system background, supports light + dark.
- Surface: elevated card background, with system material blur on iOS.
- Primary text: label color.
- Secondary text: secondaryLabel.
- Tertiary text: tertiaryLabel.
- Accent: a single hue used for primary actions and highlights. Default: system blue. User can pick from system blue, indigo, mint, orange, pink in settings.
- Semantic: success (system green), warning (system orange), destructive (system red).
- PR/achievement: system yellow.

Web tokens reference the iOS semantic colors using OKLCH approximations so light/dark parity stays close.

## Typography

- iOS: SF Pro Text for UI, SF Pro Rounded for numerics, SF Pro Display for large headings.
- Web: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", system-ui` for body. For numerics use a tabular-numbers stack.
- Scale matches iOS Dynamic Type. Base 17pt body. Headlines 22/28/34.

## Components

Shared component vocabulary (different code, same names):

- `Card`: elevated surface, 16pt radius on iOS, 12px on web. Slight shadow on web; system material on iOS.
- `StatTile`: big number + label + trend arrow. Used everywhere.
- `SetRow`: a single set entry. Weight x reps x optional RPE. Tap to edit, swipe to delete.
- `ExercisePicker`: search-backed picker with recent and favorited exercises pinned.
- `RestTimer`: prominent circular timer, haptic feedback on iOS, sound + tab title flash on web.
- `Toast`: brief confirmation. Top on iOS (matching system notifications), top-right on web.
- `Sheet`: bottom sheet on iOS, side panel or modal on web depending on viewport.

## Iconography

- SF Symbols on iOS.
- Web: use Lucide icons configured to match SF Symbol weights. A small adapter `lib/icon.tsx` maps a subset of SF Symbol names to Lucide equivalents so cross-platform documentation reads the same.

## Motion

- Default: iOS spring (response 0.4, damping 0.85).
- Avoid bouncy animations on data updates. Reserve motion for navigation transitions and rest timer ticks.
- Reduce Motion preference is honored everywhere.

## Density

- Workout logging view is high-density. Show as many sets as possible without scrolling.
- Analytics views breathe more.
- Forms (auth, settings) use standard iOS form grouping.

## Cross-platform parity

When in doubt: implement on iOS first, screenshot, then build the web equivalent to match. Do not invent web-only patterns that wouldn't translate.
