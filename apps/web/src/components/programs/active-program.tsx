"use client";

import Link from "next/link";
import { useMemo } from "react";

import { MesocycleBar } from "@/components/programs/mesocycle-bar";
import { ProgramLibrary } from "@/components/programs/program-library";
import { ProgramMasthead } from "@/components/programs/program-masthead";
import { TodayCard } from "@/components/programs/today-card";
import { WeekList } from "@/components/programs/week-list";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMyPrograms, usePosition, useProgram } from "@/lib/hooks/programs";
import type { ProgramListItem } from "@/lib/programs/types";

/**
 * Active-program "spine" for `/programs`: an Edit action, masthead, cycle bar,
 * today's slot (off the rotation position), this microcycle, then the
 * My-programs library. The spine staggers in on load via `RevealGroup`. When
 * nothing is active, the library leads so the user can activate a program.
 */
export function ActiveProgram() {
  const list = useMyPrograms();

  if (list.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (list.isError) return <p className="text-destructive">Could not load programs.</p>;

  const items = list.data?.items ?? [];
  const active = items.find((p) => p.is_active) ?? null;

  if (!active) {
    return (
      <div className="page-shell">
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
  const position = usePosition(active.id);
  const p = program.data;
  const pos = position.data ?? undefined;

  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  // The slot at the rotation position drives both the Today card and the
  // "current" highlight in the microcycle list. Prefer the position's resolved
  // slot; fall back to matching current_slot_index, then the first slot.
  const todayIdx = pos
    ? Math.max(
        0,
        p?.days.findIndex((d) => d.slot_index === pos.current_slot_index) ?? 0,
      )
    : 0;
  const todaySlot = pos?.today_slot ?? (p ? p.days[todayIdx] : undefined) ?? undefined;

  return (
    <div className="page-shell">
      <div className="mb-4 flex justify-end">
        <Link href={`/programs/${active.id}/edit`}>
          <Button type="button" variant="secondary" size="sm">
            Edit
          </Button>
        </Link>
      </div>

      {p ? (
        <RevealGroup>
          <RevealItem>
            <ProgramMasthead program={p} position={pos} hideCycleBar />
          </RevealItem>
          {pos ? (
            <RevealItem>
              <MesocycleBar position={pos} autoDeload={p.auto_deload} />
            </RevealItem>
          ) : null}
          {todaySlot ? (
            <RevealItem>
              <TodayCard
                program={p}
                day={todaySlot}
                metaMap={metaMap}
                nextTrainingSlot={pos?.next_training_slot ?? undefined}
              />
            </RevealItem>
          ) : null}
          {p.days.length > 0 ? (
            <RevealItem>
              <WeekList program={p} todayIdx={todayIdx} metaMap={metaMap} />
            </RevealItem>
          ) : null}
        </RevealGroup>
      ) : null}

      <ProgramLibrary items={items} />
    </div>
  );
}
