"use client";

import Link from "next/link";

import { DOW, exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
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
  const todayDow = DOW[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1];
  const summary = exerciseSummary(day, metaMap);
  const sets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(sets * 2.5);

  return (
    <div className="aw-today">
      <div>
        <div className="k">Today · {todayDow}</div>
        <div className="d">{day.name}</div>
        <div className="ex">
          {summary ? `${summary} · ` : ""}
          {day.exercises.length} exercise{day.exercises.length === 1 ? "" : "s"} · ~{estMin} min
        </div>
      </div>
      <Link
        href={`/programs/${program.id}/days/${day.id}`}
        className="bg-accent text-accent-foreground inline-flex h-[42px] items-center justify-center rounded-[var(--radius-button)] px-[22px] text-sm font-semibold tracking-[0.01em] hover:brightness-105"
      >
        Start
      </Link>
    </div>
  );
}
