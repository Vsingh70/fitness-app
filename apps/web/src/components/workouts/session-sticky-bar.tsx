"use client";

import Link from "next/link";

import { useActiveSession } from "@/lib/state/active-session";
import { SessionTimer } from "./session-timer";

export function SessionStickyBar() {
  const { activeSessionId, startedAtMs } = useActiveSession();
  if (!activeSessionId || !startedAtMs) return null;
  return (
    <Link
      href={`/workouts/${activeSessionId}`}
      className="bg-accent/15 text-text border-accent/30 hover:bg-accent/20 flex items-center justify-between rounded-[var(--radius-button)] border px-3 py-1 text-sm"
    >
      <span className="font-medium">Workout in progress</span>
      <SessionTimer startedAtMs={startedAtMs} className="text-xs" />
    </Link>
  );
}
