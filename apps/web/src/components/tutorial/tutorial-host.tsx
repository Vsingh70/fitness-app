"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { pageTourFor } from "./page-tours";
import { SpotlightTour } from "./spotlight-tour";
import { TOUR_STEPS } from "./tour-steps";
import { useTutorialStore } from "@/lib/hooks/use-tutorial";

/**
 * Mounts the spotlight tour and decides which tour (if any) auto-starts:
 *  - First, the WELCOME tour, once, on the first visit to Today (gated by
 *    `om.tutorial.seen`).
 *  - After the welcome tour is seen, each major screen's PAGE tour auto-runs the
 *    first time the user lands on it (gated per-route in `om.tutorial.pages`).
 * Backend has no "new user" signal, so first-run is detected client-side.
 */
export function TutorialHost() {
  const pathname = usePathname();
  const seen = useTutorialStore((s) => s.seen);
  const seenPages = useTutorialStore((s) => s.seenPages);
  const running = useTutorialStore((s) => s.running);
  const startWelcome = useTutorialStore((s) => s.startWelcome);
  const startPage = useTutorialStore((s) => s.startPage);

  useEffect(() => {
    if (running) return undefined;

    // Welcome tour takes precedence on the first Today visit.
    if (!seen && pathname === "/") {
      const t = window.setTimeout(() => startWelcome(TOUR_STEPS), 350);
      return () => window.clearTimeout(t);
    }

    // Otherwise, run a per-page tour the first time this route is visited.
    if (seen) {
      const tour = pageTourFor(pathname);
      if (tour && !seenPages.includes(tour.pageId)) {
        const t = window.setTimeout(() => startPage(tour.pageId, tour.steps), 350);
        return () => window.clearTimeout(t);
      }
    }
    return undefined;
  }, [seen, seenPages, running, pathname, startWelcome, startPage]);

  return <SpotlightTour />;
}
