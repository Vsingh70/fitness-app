"use client";

import Link from "next/link";

import { DOW, exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
import type { Program } from "@/lib/programs/types";

/**
 * "This week" (`.aw-week`): one row per program day with its day-of-week, name +
 * muscle summary, exercise count, and a Done / Today / Planned status. Completed
 * rows dim; the current day is accented.
 */
export function WeekList({
  program,
  todayIdx,
  metaMap,
}: {
  program: Program;
  todayIdx: number;
  metaMap: ExMetaMap;
}) {
  return (
    <div className="aw-week">
      <div className="aw-week-h">
        <span className="t">This week</span>
        <Link href="/workouts/calendar" className="pw-link">
          Full calendar
        </Link>
      </div>
      {program.days.map((day, idx) => {
        const status: "done" | "today" | "planned" =
          idx < todayIdx ? "done" : idx === todayIdx ? "today" : "planned";
        const summary = exerciseSummary(day, metaMap);
        return (
          <Link
            key={day.id}
            href={`/programs/${program.id}/days/${day.id}`}
            className={`aw-day ${status === "done" ? "done" : status === "today" ? "today" : ""}`}
          >
            <span className="dow">{DOW[idx % 7]}</span>
            <div>
              <div className="nm">{day.name}</div>
              {summary ? <div className="mus">{summary}</div> : null}
            </div>
            <span className="cnt">{day.exercises.length} ex</span>
            <span className="st">
              {status === "today" ? "Today" : status === "done" ? "Done" : "Planned"}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
