"use client";

import Link from "next/link";

import { DOW, exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
import type { Program } from "@/lib/programs/types";

/**
 * "This microcycle" (`.aw-week`): one row per slot in the current microcycle.
 * Rest slots render italic and muted; training slots show name, muscle summary,
 * exercise count, and a Done / Today / Planned status. Completed rows dim and the
 * current slot is accented.
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
        <span className="t">This microcycle</span>
        <Link href="/workouts/calendar" className="pw-link">
          Full calendar
        </Link>
      </div>
      {program.days.map((day, idx) => {
        const status: "done" | "today" | "planned" =
          idx < todayIdx ? "done" : idx === todayIdx ? "today" : "planned";
        const summary = exerciseSummary(day, metaMap);

        if (day.is_rest_day) {
          return (
            <div key={day.id} className={`aw-day rest ${status === "today" ? "today" : ""}`}>
              <span className="dow">{DOW[idx % 7]}</span>
              <div>
                <div className="nm">{day.name}</div>
                <div className="mus">Rest day</div>
              </div>
              <span className="cnt" />
              <span className="st">{status === "today" ? "Today" : ""}</span>
            </div>
          );
        }

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
            <span className="cnt">{day.exercises.length ? `${day.exercises.length} ex` : ""}</span>
            <span className="st">
              {status === "today" ? "Today" : status === "done" ? "Done" : ""}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
