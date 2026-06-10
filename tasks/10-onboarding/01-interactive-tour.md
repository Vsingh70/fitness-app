# 10.01 Interactive product tour

## Context

There is a basic tour already (`apps/web/src/components/tutorial/tour-steps.ts` plus the help content). It is a short static set of steps. We want a more robust, interactive tour that actually teaches how to use the app: how to log a workout, build or pick a program, read analytics, plan and log nutrition, and connect a watch.

Reference: existing `components/tutorial/` and `app/(app)/help/help-content.ts`, `00-overview/design-system.md`.

## Goal

A guided, interactive tour that walks a new user through the core flows with element highlighting, real anchored steps per page, progress, skip and resume, and a way to replay it later from help.

## Behavior

- Multi step overlay that highlights a real target element, shows a title and one or two lines of copy, and a Next, Back, Skip control with a progress indicator.
- Interactive, not just text: where it makes sense a step waits for the user to perform the action (open the add set sheet, tap a meal complete, open the program builder) before advancing, with a Skip step escape so no one gets stuck.
- Page aware: steps are grouped by route (Today, Workout, Programs, Analytics, Nutrition, Settings). Navigating to a page can start that page's mini tour.
- First run: launches automatically on first sign in after onboarding. Persist completion and current step server side or in user settings so it does not relaunch on every device, and so a half finished tour can resume.
- Replayable: a "Take the tour" entry in help restarts it. Per page "Show me" links can launch just that page's steps.
- Respects reduced motion and is keyboard navigable. Anchored tooltips reposition on resize and scroll.

## Data and API

- Store tour state on the user: `tour_completed` bool and `tour_progress` (last route and step) so it survives devices. Add to the user settings schema and the me endpoint, or a small `user_onboarding` row if cleaner.
- No heavy backend. The content lives in the web app; only progress and completion persist.

## Web implementation

- Replace the static step list with a tour engine: a registry of steps keyed by route, each step describing its anchor selector, copy, optional required action, and placement.
- A provider that drives the overlay, manages focus, and writes progress.
- Author real steps for: Today (rings, readiness, quick add), Workout logging (add exercise, add set, finish), Programs (pick template, builder basics, schedule), Analytics (volume, strong and weak points), Nutrition (plan vs flexible, mark complete, track a meal), Settings (connect Fitbit via Google, units).
- Keep copy in the same content file style as `help-content.ts`. Follow the no dashes style rule.

## Deliverables

1. Tour engine with anchored, interactive, page grouped steps and progress, skip, resume, replay.
2. Persisted tour state on the user (schema, migration if needed, me endpoint field).
3. Authored steps covering the six core areas above.
4. Help entry to replay the tour and per page "Show me" launchers.
5. Tests: step advancement including action gated steps, skip, resume from saved progress, and that completion stops auto relaunch.

## Acceptance criteria

- A brand new user is walked through logging a set, looking at analytics, and planning a meal without reading docs.
- The tour can be skipped at any step and resumed later from where it stopped.
- It can be replayed from help, and a single page tour can be launched on demand.
- Highlights stay correctly anchored across resize, scroll, and route changes.

## Dependencies

- Existing web app pages: Today, Workout, Programs, Analytics, Nutrition, Settings.
- `06.05` and `06.06` for the nutrition steps to match the new flows.

## Out of scope

- iOS tour (follow-up under `08-ios/`).
- Video walkthroughs.
