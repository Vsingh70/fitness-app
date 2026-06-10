# 10.02 Public landing page

## Context

The app opens straight into sign in. There is no public page that explains what the app is or shows how you manage your training and nutrition with it. We want a landing page that introduces the product, shows the core flows, and leads into sign in.

Reference: `00-overview/design-system.md`, `tasks/web/` design explorations, `app/(auth)/` sign in.

## Goal

A fast, public, unauthenticated landing page at the web root that explains the app, shows how it is used to manage workouts, programs, progression, analytics, and nutrition, and routes visitors to sign in or request access.

## Content

- Hero: one line on what the app is (a training operating system for you and your gym buddies), a short subline, and a primary call to action into sign in.
- How it is managed: a short walkthrough of the loop, each with a visual or screenshot.
  - Plan: build or pick a program, set it to periodized or just keep progressing.
  - Train: log workouts fast, get progression recommendations.
  - Eat: plan meals or track flexibly, log a planned day in a tap.
  - Recover: connect a watch via Google Health, see readiness.
  - Review: analytics for volume, strong and weak points, stagnation.
- Trust and management line: it is self hosted and private, built for a small group, your data is yours.
- Footer: links to sign in, help, privacy.

## Implementation

- New public route at the web root, outside the authenticated `(app)` group, so it renders without a session. Keep the existing `(app)` and `(auth)` groups intact. Authenticated users hitting the root can be sent to Today.
- Server rendered and static where possible for speed and for link previews. Add reasonable metadata and an Open Graph image.
- Reuse the design tokens and components so it matches the app. Follow the no dashes style rule in all copy.
- Use real screenshots or simple mock visuals from the existing `tasks/web/` explorations as placeholders where finished screens are not ready.
- Responsive and accessible.

## Deliverables

1. Public landing route at the web root with the sections above.
2. Routing so signed in users go to Today and signed out users see the landing page, with clear calls to action into sign in.
3. Metadata and an Open Graph image for sharing.
4. Reused components and tokens, responsive layout.
5. A basic test or check that the page renders unauthenticated and that the primary call to action links to sign in.

## Acceptance criteria

- A logged out visitor lands on a page that explains the app and how it is used, then can reach sign in in one click.
- The page is fast (server or static rendered) and looks consistent with the app.
- It is responsive and has correct share metadata.

## Dependencies

- Existing auth and the `(app)` route group.
- `10.01 Interactive product tour` is complementary but not required.

## Out of scope

- Marketing site CMS or blog.
- Pricing or billing (this is a private app).
- iOS marketing assets.
