"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ProgramMasthead } from "@/components/programs/program-masthead";
import { TodayCard } from "@/components/programs/today-card";
import { WeekList } from "@/components/programs/week-list";
import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useProgram, usePosition } from "@/lib/hooks/programs";

/**
 * Read-only overview of a single program (`/programs/[id]`): masthead + cycle
 * bar, today's slot (off the rotation position), this microcycle — with an Edit
 * action into the builder. The library is only shown on the top-level
 * `/programs` overview, not here.
 */
export function ProgramOverview({ programId }: { programId: string }) {
  const program = useProgram(programId);
  const position = usePosition(programId);
  const p = program.data;
  const pos = position.data ?? undefined;

  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  const todayIdx = pos
    ? Math.max(0, p?.days.findIndex((d) => d.slot_index === pos.current_slot_index) ?? 0)
    : 0;
  const todaySlot = pos?.today_slot ?? (p ? p.days[todayIdx] : undefined) ?? undefined;

  if (program.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (program.isError || !p) return <p className="text-destructive">Could not load program.</p>;

  return (
    <div className="page-shell">
      <div className="mb-5 flex items-center justify-between gap-4">
        <p className="text-text-tertiary text-xs">
          <Link href="/programs" className="hover:text-text">
            Programs
          </Link>{" "}
          ›
        </p>
        <Link href={`/programs/${p.id}/edit`}>
          <Button type="button" variant="secondary" size="sm">
            Edit
          </Button>
        </Link>
      </div>

      <ProgramMasthead
        program={p}
        position={pos}
        kicker={p.is_active ? "Active program" : "Program"}
      />
      {todaySlot ? (
        <TodayCard
          program={p}
          day={todaySlot}
          metaMap={metaMap}
          nextTrainingSlot={pos?.next_training_slot ?? undefined}
        />
      ) : null}
      {p.days.length > 0 ? <WeekList program={p} todayIdx={todayIdx} metaMap={metaMap} /> : null}
    </div>
  );
}
