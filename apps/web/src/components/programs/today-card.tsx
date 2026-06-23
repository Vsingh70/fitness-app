"use client";

import Link from "next/link";

import { exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
import type { Program, ProgramDay } from "@/lib/programs/types";

/**
 * Today's session card (`.aw-today`): the next planned day with its exercise
 * summary and a big Start action into the per-day detail.
 */
export function TodayCard({
  program,
  day,
  metaMap,
}: {
  program: Program;
  day: ProgramDay;
  metaMap: ExMetaMap;
}) {
  const todayName = new Date().toLocaleDateString("en-US", { weekday: "long" });
  const summary = exerciseSummary(day, metaMap);
  const sets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(sets * 2.5);

  if (day.is_rest_day) {
    return (
      <div className="aw-today">
        <div>
          <div className="k">Today · {todayName}</div>
          <div className="d">{day.name}</div>
          <div className="ex">Rest day — no session planned.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="aw-today">
      <div>
        <div className="k">Today · {todayName}</div>
        <div className="d">{day.name}</div>
        <div className="ex">
          {summary ? `${summary} · ` : ""}
          {day.exercises.length} exercise{day.exercises.length === 1 ? "" : "s"} · ~{estMin} min
        </div>
      </div>
      <Link
        href={`/programs/${program.id}/days/${day.id}`}
        className="bg-accent text-accent-foreground inline-flex h-[50px] items-center justify-center gap-2 rounded-[var(--radius-button)] px-[22px] text-[15px] font-semibold tracking-[0.01em] hover:brightness-105"
      >
        <svg width={16} height={16} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M6 4l14 8-14 8z" />
        </svg>
        Start
      </Link>
    </div>
  );
}
