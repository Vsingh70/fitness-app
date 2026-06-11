"use client";

import { create } from "zustand";

interface ActiveSessionState {
  /** Session id of the in-progress workout, if any. */
  activeSessionId: string | null;
  /** Server-side `started_at` epoch ms; used by SessionTimer + SessionStickyBar. */
  startedAtMs: number | null;
  setActive: (sessionId: string, startedAtIso: string) => void;
  clearActive: () => void;
}

export const useActiveSession = create<ActiveSessionState>((set) => ({
  activeSessionId: null,
  startedAtMs: null,
  setActive: (sessionId, startedAtIso) =>
    set({ activeSessionId: sessionId, startedAtMs: new Date(startedAtIso).getTime() }),
  clearActive: () => set({ activeSessionId: null, startedAtMs: null }),
}));
