"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ProgramMasthead } from "@/components/programs/program-masthead";
import { TodayCard } from "@/components/programs/today-card";
import { WeekList } from "@/components/programs/week-list";
import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMesocycle, useProgram } from "@/lib/hooks/programs";

/**
 * Read-only overview of a single program (`/programs/[id]`): masthead + mesocycle
 * bar, today's session, this week — with an Edit action into the builder. The
 * library is only shown on the top-level `/programs` overview, not here.
 */
export function ProgramOverview({ programId }: { programId: string }) {
  const program = useProgram(programId);
  const meso = useMesocycle(programId);
  const p = program.data;

  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  if (program.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (program.isError || !p) return <p className="text-destructive">Could not load program.</p>;

  return (
    <div className="mx-auto max-w-4xl">
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
        meso={meso.data ?? undefined}
        kicker={p.is_active ? "Active program" : "Program"}
      />
      {p.days.length > 0 ? <TodayCard program={p} day={p.days[0]!} metaMap={metaMap} /> : null}
      {p.days.length > 0 ? <WeekList program={p} todayIdx={0} metaMap={metaMap} /> : null}
    </div>
  );
}
