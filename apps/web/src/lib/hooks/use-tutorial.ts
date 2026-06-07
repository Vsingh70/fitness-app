"use client";

import { create } from "zustand";

import type { TourStep } from "@/components/tutorial/tour-steps";

/**
 * Onboarding tour state. There is no server "is new user" signal, so first-run
 * is detected purely client-side via localStorage.
 *
 * Two layers:
 *  - The WELCOME tour (the original 60-second nav overview) auto-runs once on the
 *    Today screen, gated by `om.tutorial.seen`. Replayable from Help.
 *  - PER-PAGE tours: each major screen has a short tour that auto-runs the first
 *    time the user lands on it, gated by a per-route flag in `om.tutorial.pages`
 *    (a JSON array of route ids already seen). Page tours only start after the
 *    welcome tour has been seen, so a brand-new user gets the welcome tour first.
 *
 * Mirrors the app's existing localStorage convention (`om.*` keys, see
 * use-theme.ts / use-prefs.ts).
 */

const SEEN_KEY = "om.tutorial.seen";
const PAGES_KEY = "om.tutorial.pages";

function readWelcomeSeen(): boolean {
  if (typeof window === "undefined") return true; // never auto-run during SSR
  return window.localStorage.getItem(SEEN_KEY) === "true";
}

function readSeenPages(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(PAGES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writeSeenPages(pages: string[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PAGES_KEY, JSON.stringify(pages));
}

/** Identifies the welcome tour vs a per-page tour, for persistence on finish. */
type ActiveKind = { kind: "welcome" } | { kind: "page"; pageId: string };

interface TutorialState {
  /** Whether the user has completed or dismissed the welcome tour. */
  seen: boolean;
  /** Route ids whose page tour the user has already seen. */
  seenPages: string[];
  /** Whether a tour is currently running. */
  running: boolean;
  /** The steps of the currently-running (or last-run) tour. */
  steps: TourStep[];
  /** What the running tour is, so finish() can persist the right flag. */
  active: ActiveKind | null;

  /** Start the welcome tour (first-run auto-start + Help "replay"). */
  startWelcome: (steps: TourStep[]) => void;
  /** Start a page tour on first visit. */
  startPage: (pageId: string, steps: TourStep[]) => void;
  /** Finish or skip the running tour; persists the matching seen flag. */
  finish: () => void;

  /** Clear the welcome flag so it auto-runs again on next Today visit. */
  reset: () => void;
  /** Clear all per-page seen flags so every page tour runs again. */
  resetPages: () => void;
  /** True if this page's tour hasn't been seen yet. */
  hasSeenPage: (pageId: string) => boolean;
}

export const useTutorialStore = create<TutorialState>((set, get) => ({
  seen: readWelcomeSeen(),
  seenPages: readSeenPages(),
  running: false,
  steps: [],
  active: null,

  startWelcome: (steps) => set({ running: true, steps, active: { kind: "welcome" } }),
  startPage: (pageId, steps) => set({ running: true, steps, active: { kind: "page", pageId } }),

  finish: () => {
    const { active, seenPages } = get();
    if (typeof window !== "undefined" && active?.kind === "welcome") {
      window.localStorage.setItem(SEEN_KEY, "true");
    }
    if (active?.kind === "page" && !seenPages.includes(active.pageId)) {
      const next = [...seenPages, active.pageId];
      writeSeenPages(next);
      set({ running: false, active: null, seenPages: next, seen: true });
      return;
    }
    set({
      running: false,
      active: null,
      // Completing the welcome tour also marks it seen in state.
      seen: active?.kind === "welcome" ? true : get().seen,
    });
  },

  reset: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(SEEN_KEY);
    }
    set({ seen: false });
  },

  resetPages: () => {
    writeSeenPages([]);
    set({ seenPages: [] });
  },

  hasSeenPage: (pageId) => get().seenPages.includes(pageId),
}));
