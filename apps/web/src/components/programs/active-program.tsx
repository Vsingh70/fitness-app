"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ProgramLibrary } from "@/components/programs/program-library";
import { ProgramMasthead } from "@/components/programs/program-masthead";
import { TodayCard } from "@/components/programs/today-card";
import { WeekList } from "@/components/programs/week-list";
import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMesocycle, useMyPrograms, useProgram } from "@/lib/hooks/programs";
import type { ProgramListItem } from "@/lib/programs/types";

/**
 * Active-program "spine" for `/programs`: an Edit action, masthead + mesocycle
 * bar, today's session, this week, then the My-programs library. When nothing is
 * active, the library leads so the user can activate a program.
 */
export function ActiveProgram() {
  const list = useMyPrograms();

  if (list.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (list.isError) return <p className="text-destructive">Could not load programs.</p>;

  const items = list.data?.items ?? [];
  const active = items.find((p) => p.is_active) ?? null;

  if (!active) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="pw-kicker">Programs</div>
        <h1 className="pw-serif" style={{ fontSize: 32, margin: "8px 0 0" }}>
          No active program
        </h1>
        <p className="text-text-secondary mt-2 text-sm">
          Activate one below, or browse templates to start.
        </p>
        <ProgramLibrary items={items} />
      </div>
    );
  }

  return <Spine active={active} items={items} />;
}

function Spine({ active, items }: { active: ProgramListItem; items: ProgramListItem[] }) {
  const program = useProgram(active.id);
  const meso = useMesocycle(active.id);
  const p = program.data;

  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();
  const todayIdx = 0;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex justify-end">
        <Link href={`/programs/${active.id}/edit`}>
          <Button type="button" variant="secondary" size="sm">
            Edit
          </Button>
        </Link>
      </div>

      {p ? <ProgramMasthead program={p} meso={meso.data ?? undefined} /> : null}
      {p && p.days.length > 0 ? (
        <TodayCard program={p} day={p.days[todayIdx]!} metaMap={metaMap} />
      ) : null}
      {p && p.days.length > 0 ? (
        <WeekList program={p} todayIdx={todayIdx} metaMap={metaMap} />
      ) : null}

      <ProgramLibrary items={items} />
    </div>
  );
}
