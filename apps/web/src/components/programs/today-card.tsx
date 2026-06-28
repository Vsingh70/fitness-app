"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import type { Program, ProgramDay } from "@/lib/programs/types";

const MotionLink = motion.create(Link);

/**
 * Today's session card (`.aw-today`): the slot at the current rotation position.
 * A rest slot shows a quiet "Rest day" state and names the next training slot; a
 * training slot shows its exercise summary and a Start action into the per-slot
 * detail. The Start affordance settles on tap (no idle motion); under reduced
 * motion the tap transform is dropped.
 */
export function TodayCard({
  program,
  day,
  metaMap,
  nextTrainingSlot,
}: {
  program: Program;
  day: ProgramDay;
  metaMap: ExMetaMap;
  nextTrainingSlot?: ProgramDay | null;
}) {
  const { reduced } = useReducedMotionSafe();
  const todayName = new Date().toLocaleDateString("en-US", { weekday: "long" });

  if (day.is_rest_day) {
    return (
      <div className="aw-today">
        <div>
          <div className="k">Today · {todayName}</div>
          <div className="d" style={{ fontStyle: "italic" }}>
            Rest day
          </div>
          <div className="ex">
            {nextTrainingSlot ? `Next up: ${nextTrainingSlot.name}.` : "No session planned today."}
          </div>
        </div>
      </div>
    );
  }

  const summary = exerciseSummary(day, metaMap);
  const sets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(sets * 2.5);

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
      <MotionLink
        href={`/programs/${program.id}/days/${day.id}`}
        className="bg-accent text-accent-foreground inline-flex h-[50px] items-center justify-center gap-2 rounded-[var(--radius-button)] px-[22px] text-[15px] font-semibold tracking-[0.01em] hover:brightness-105"
        transition={snappy}
        whileTap={reduced ? undefined : { scale: 0.985 }}
      >
        <svg width={16} height={16} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M6 4l14 8-14 8z" />
        </svg>
        Start
      </MotionLink>
    </div>
  );
}
