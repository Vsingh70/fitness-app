"use client";

import { create } from "zustand";

/**
 * First-login onboarding state. There is no server "is new user" signal, so we
 * detect first run purely client-side: if `seen` is false, the spotlight tour
 * auto-starts once on the Today screen. The Help page can reset `seen` to replay.
 *
 * Mirrors the app's existing localStorage convention (`om.*` keys, see
 * use-theme.ts / use-prefs.ts).
 */

const SEEN_KEY = "om.tutorial.seen";

function readSeen(): boolean {
  if (typeof window === "undefined") return true; // never auto-run during SSR
  return window.localStorage.getItem(SEEN_KEY) === "true";
}

interface TutorialState {
  /** Whether the user has completed or dismissed the onboarding tour. */
  seen: boolean;
  /** Whether the spotlight tour is currently running. */
  running: boolean;
  /** Start the tour (used by first-run auto-start and the Help "replay" button). */
  start: () => void;
  /** Finish or skip the tour; persists `seen=true` so it won't auto-run again. */
  finish: () => void;
  /** Clear the seen flag so the tour will auto-run again on next Today visit. */
  reset: () => void;
}

export const useTutorialStore = create<TutorialState>((set) => ({
  seen: readSeen(),
  running: false,
  start: () => set({ running: true }),
  finish: () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SEEN_KEY, "true");
    }
    set({ running: false, seen: true });
  },
  reset: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(SEEN_KEY);
    }
    set({ seen: false });
  },
}));
