/**
 * Per-page first-visit tours. The first time a user lands on a major screen, a
 * short tour auto-runs (gated per-route in the tutorial store). Content is
 * derived from the single source of truth in the Help page (`HELP_SECTIONS`) so
 * the in-app tour and the written guide never drift.
 *
 * A page tour opens by spotlighting that page's nav item (always present in the
 * app shell, so targeting is robust at any viewport), then shows centered cards
 * for "what it's for" + a worked example. Centered cards avoid fragile
 * page-internal element targeting that breaks when a page's layout changes.
 */

import { HELP_SECTIONS, type HelpSection } from "@/app/(app)/help/help-content";
import type { TourStep } from "./tour-steps";

/** Maps a page's nav item so the opening step can spotlight it. */
const NAV_TARGET_BY_HREF: Record<string, string> = {
  "/": "nav-today",
  "/workouts": "nav-workouts",
  "/programs": "nav-programs",
  "/nutrition": "nav-nutrition",
  "/analytics": "nav-insights",
  "/settings": "nav-settings",
};

function stepsFromSection(section: HelpSection): TourStep[] {
  const navTarget = NAV_TARGET_BY_HREF[section.href] ?? null;
  // Keep the top 3 key actions so the tour stays short.
  const actions = section.keyActions.slice(0, 3);
  return [
    {
      target: navTarget,
      title: section.page,
      body: section.whatItsFor,
    },
    {
      target: null,
      title: "What you can do here",
      body: actions.map((a) => `• ${a}`).join("\n"),
    },
    {
      target: null,
      title: `Example · ${section.example.title}`,
      body: section.example.steps.map((s, i) => `${i + 1}. ${s}`).join("\n"),
    },
  ];
}

/**
 * Per-route tour steps, keyed by pathname. Built from HELP_SECTIONS. The Today
 * route ("/") is intentionally EXCLUDED here — Today's first-visit experience is
 * the welcome tour, not a page tour, so it isn't double-shown.
 */
export const PAGE_TOURS: Record<string, TourStep[]> = Object.fromEntries(
  HELP_SECTIONS.filter((s) => s.href !== "/").map((s) => [s.href, stepsFromSection(s)]),
);

/** The steps for a given pathname, or null if that route has no page tour. */
export function pageTourFor(pathname: string): { pageId: string; steps: TourStep[] } | null {
  const steps = PAGE_TOURS[pathname];
  return steps ? { pageId: pathname, steps } : null;
}
