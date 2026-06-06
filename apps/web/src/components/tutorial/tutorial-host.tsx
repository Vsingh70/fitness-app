"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { SpotlightTour } from "./spotlight-tour";
import { useTutorialStore } from "@/lib/hooks/use-tutorial";

/**
 * Mounts the spotlight tour and auto-starts it once, on the first visit to the
 * Today screen after sign-in (detected via the `om.tutorial.seen` flag, since
 * the backend has no "new user" signal). The nav anchors the tour points at
 * live in the app shell, so the Today screen is where every target is visible.
 */
export function TutorialHost() {
  const pathname = usePathname();
  const seen = useTutorialStore((s) => s.seen);
  const running = useTutorialStore((s) => s.running);
  const start = useTutorialStore((s) => s.start);

  useEffect(() => {
    if (!seen && !running && pathname === "/") {
      // Let the page paint first so the spotlight measures correct positions.
      const t = window.setTimeout(start, 350);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [seen, running, pathname, start]);

  return <SpotlightTour />;
}
