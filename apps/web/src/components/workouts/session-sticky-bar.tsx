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
      className="bg-surface-elevated text-text border-border hover:bg-surface inline-flex items-center gap-3 rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-semibold tracking-[0.08em] uppercase"
    >
      <span className="bg-accent inline-block h-[7px] w-[7px] rounded-full" aria-hidden />
      <span>Workout in progress</span>
      <SessionTimer
        startedAtMs={startedAtMs}
        className="text-text-secondary font-serif text-[13px] font-medium tracking-normal normal-case"
      />
    </Link>
  );
}
