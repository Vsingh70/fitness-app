"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMyPrograms, usePosition } from "@/lib/hooks/programs";
import { useCreateEmptySession } from "@/lib/hooks/workouts";
import { useActiveSession } from "@/lib/state/active-session";
import type { ProgramDay } from "@/lib/programs/types";

/**
 * The Train tab's "today's session" card. Reads the active program's rotation
 * position (`usePosition`) to name the current slot and summarize its exercises,
 * then a Start that opens a freestyle empty session (the slot-prefilled start is
 * part of the deferred logging loop). Handles the no-active-program and rest-day
 * states gracefully.
 */
export function TrainTodayCard() {
  const programs = useMyPrograms();
  const activeProgram = programs.data?.items.find((p) => p.is_active) ?? null;
  const position = usePosition(activeProgram?.id);

  const router = useRouter();
  const createEmpty = useCreateEmptySession();
  const setActive = useActiveSession((s) => s.setActive);

  const onStart = () => {
    createEmpty.mutate(
      {},
      {
        onSuccess: (session) => {
          setActive(session.id, session.started_at);
          router.push(`/workouts/${session.id}`);
        },
      },
    );
  };

  // Loading shell — the programs list resolves first, then the position.
  if (programs.isLoading || (activeProgram && position.isLoading)) {
    return (
      <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-7">
        <p className="text-text-secondary text-sm">Loading today’s session…</p>
      </div>
    );
  }

  // No active program: route to Programs onboarding rather than show an empty hero.
  if (!activeProgram) {
    return (
      <div className="border-border bg-surface-elevated grid gap-6 rounded-[var(--radius-card)] border p-7 md:grid-cols-[1fr_auto] md:items-end">
        <div className="min-w-0">
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
            Train
          </span>
          <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
            No active program
          </h2>
          <p className="text-text-secondary mt-3 max-w-[34rem] text-sm">
            Pick a program to drive your sessions, or start a freestyle workout right now.
          </p>
        </div>
        <div className="flex flex-col gap-2 md:items-end">
          <Button size="lg" onClick={onStart} disabled={createEmpty.isPending}>
            {createEmpty.isPending ? "Starting…" : "Start empty workout"}
          </Button>
          <Link
            href="/programs"
            className="text-text-secondary hover:text-text text-[13px] font-medium"
          >
            Browse programs →
          </Link>
        </div>
      </div>
    );
  }

  const pos = position.data;
  const slot = pos?.today_slot ?? null;
  const isRest = pos?.is_rest_day ?? slot?.is_rest_day ?? false;
  const cycleLabel =
    pos && pos.current_microcycle_number ? `Cycle ${pos.current_microcycle_number}` : null;

  return (
    <TrainSlotCard
      programName={activeProgram.name}
      slot={slot}
      isRest={isRest}
      inDeload={pos?.in_deload ?? false}
      nextTrainingSlotName={pos?.next_training_slot?.name ?? null}
      cycleLabel={cycleLabel}
      onStart={onStart}
      starting={createEmpty.isPending}
    />
  );
}

function TrainSlotCard({
  programName,
  slot,
  isRest,
  inDeload,
  nextTrainingSlotName,
  cycleLabel,
  onStart,
  starting,
}: {
  programName: string;
  slot: ProgramDay | null;
  isRest: boolean;
  inDeload: boolean;
  nextTrainingSlotName: string | null;
  cycleLabel: string | null;
  onStart: () => void;
  starting: boolean;
}) {
  const exerciseIds = useMemo(
    () => (slot && !isRest ? slot.exercises.map((e) => e.exercise_id) : []),
    [slot, isRest],
  );
  const meta = useExerciseMeta(exerciseIds);

  const summary = useMemo(() => {
    if (!slot || isRest) return [];
    return slot.exercises
      .slice()
      .sort((a, b) => a.position - b.position)
      .map((e) => meta.data?.get(e.exercise_id)?.name ?? null)
      .filter((name): name is string => !!name);
  }, [slot, isRest, meta.data]);

  const slotName = slot?.name ?? "Today";
  const exerciseCount = slot && !isRest ? slot.exercises.length : 0;

  return (
    <div className="border-border bg-surface-elevated relative grid gap-6 overflow-hidden rounded-[var(--radius-card)] border p-7 md:grid-cols-[1fr_auto] md:items-end">
      <div className="min-w-0">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
          {isRest ? "Train · Rest" : `Train · ${slotName}`}
        </span>
        <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
          {isRest ? "Rest day" : programName}
        </h2>

        {isRest ? (
          <p className="text-text-secondary mt-3 max-w-[34rem] text-sm">
            {nextTrainingSlotName
              ? `Next up: ${nextTrainingSlotName}. Take it easy or start a freestyle workout.`
              : "Take it easy or start a freestyle workout if you’re feeling it."}
          </p>
        ) : (
          <>
            <div className="text-text-secondary mt-4 flex flex-wrap items-center gap-4 text-sm">
              <span>
                <b className="text-text font-serif font-medium tabular-nums">{exerciseCount}</b>{" "}
                exercise{exerciseCount === 1 ? "" : "s"}
              </span>
              {inDeload ? (
                <span className="text-warning inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-warning)_45%,transparent)] px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                  Deload
                </span>
              ) : null}
            </div>
            {summary.length > 0 ? (
              <p className="text-text-tertiary mt-2 max-w-[34rem] truncate text-sm">
                {summary.join(" · ")}
              </p>
            ) : null}
          </>
        )}
      </div>

      {cycleLabel ? (
        <span className="border-border bg-surface text-text-secondary absolute top-6 right-6 inline-flex h-[28px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase">
          {cycleLabel}
        </span>
      ) : null}

      <div className="flex flex-col gap-2 md:items-end">
        <Button size="lg" onClick={onStart} disabled={starting}>
          {starting ? "Starting…" : isRest ? "Start empty workout" : "Start workout →"}
        </Button>
        <Link href="/calendar" className="text-text-secondary hover:text-text text-[13px] font-medium">
          Open calendar →
        </Link>
      </div>
    </div>
  );
}
