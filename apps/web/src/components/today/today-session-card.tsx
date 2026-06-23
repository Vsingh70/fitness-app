"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { exerciseSummary } from "@/components/programs/day-meta";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMyPrograms, usePosition, useProgram } from "@/lib/hooks/programs";
import { useStartProgramSession } from "@/lib/hooks/workouts";
import { useActiveSession } from "@/lib/state/active-session";
import type { Program, ProgramDay, ProgramPosition } from "@/lib/programs/types";

/**
 * Today's session card on the command center: the active program's current
 * rotation slot. Drives off `usePosition` (with `useProgram` for exercise
 * detail). A training slot offers Start (start-from-slot, advancing the
 * rotation on finish); a rest slot shows a quiet rest state and names the next
 * training slot; no active program routes to Programs onboarding.
 */
export function TodaySessionCard() {
  const list = useMyPrograms();
  const items = list.data?.items ?? [];
  const active = items.find((p) => p.is_active) ?? null;

  if (list.isLoading) {
    return <Shell><p className="text-text-secondary text-sm">Loading today’s session…</p></Shell>;
  }

  if (!active) {
    return (
      <Shell>
        <Kicker>Today</Kicker>
        <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
          No active program
        </h2>
        <p className="text-text-secondary mt-3 max-w-[34rem] text-sm">
          Pick a program to get a session here every day. The active program drives your rotation.
        </p>
        <div className="mt-5 flex flex-col gap-2 md:flex-row md:items-center">
          <Link href="/programs">
            <Button size="lg">Pick a program →</Button>
          </Link>
        </div>
      </Shell>
    );
  }

  return <ActiveSlot programId={active.id} />;
}

function ActiveSlot({ programId }: { programId: string }) {
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

  // Resolve the slot at the rotation position; prefer the server-resolved slot,
  // fall back to matching current_slot_index, then the first slot.
  const todaySlot = useMemo<ProgramDay | undefined>(() => {
    if (pos?.today_slot) return pos.today_slot;
    if (!p) return undefined;
    const byIndex = p.days.find((d) => d.slot_index === pos?.current_slot_index);
    return byIndex ?? p.days[0];
  }, [p, pos]);

  if (program.isLoading || position.isLoading) {
    return <Shell><p className="text-text-secondary text-sm">Loading today’s session…</p></Shell>;
  }
  if (!p || !todaySlot) {
    return (
      <Shell>
        <Kicker>Today</Kicker>
        <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
          {p?.name ?? "Your program"}
        </h2>
        <p className="text-text-secondary mt-3 text-sm">
          This program has no slots yet. Add training days in the builder.
        </p>
        <div className="mt-5">
          <Link href={`/programs/${programId}/edit`}>
            <Button size="lg" variant="secondary">
              Open builder →
            </Button>
          </Link>
        </div>
      </Shell>
    );
  }

  if (todaySlot.is_rest_day) {
    const next = pos?.next_training_slot ?? null;
    return (
      <Shell>
        <Kicker>Today · Rest</Kicker>
        <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight italic md:text-[32px]">
          Rest day
        </h2>
        <p className="text-text-secondary mt-3 max-w-[34rem] text-sm">
          {next ? (
            <>
              Recover today. Next up:{" "}
              <span className="text-text font-medium">{next.name}</span>.
            </>
          ) : (
            "Recover today — no session planned."
          )}
        </p>
        <div className="mt-5">
          <Link
            href="/programs"
            className="text-text-secondary hover:text-text text-[13px] font-medium"
          >
            View program →
          </Link>
        </div>
      </Shell>
    );
  }

  return (
    <TrainingSlot
      program={p}
      day={todaySlot}
      position={pos}
      summary={exerciseSummary(todaySlot, metaMap)}
    />
  );
}

function TrainingSlot({
  program,
  day,
  position,
  summary,
}: {
  program: Program;
  day: ProgramDay;
  position: ProgramPosition | undefined;
  summary: string;
}) {
  const router = useRouter();
  const start = useStartProgramSession();
  const setActive = useActiveSession((s) => s.setActive);
  const pushToast = useToastStore((s) => s.push);

  const sets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(sets * 2.5);
  const cycleLabel =
    position?.current_microcycle_number != null
      ? `Microcycle ${position.current_microcycle_number}`
      : null;

  const onStart = () => {
    start.mutate(program.id, {
      onSuccess: (session) => {
        setActive(session.id, session.started_at);
        router.push(`/workouts/${session.id}`);
      },
      onError: () => {
        pushToast({ kind: "error", message: "Could not start the session." });
      },
    });
  };

  return (
    <Shell>
      <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
        <div className="min-w-0">
          <Kicker>Today · {program.name}</Kicker>
          <h2 className="mt-1.5 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
            {day.name}
          </h2>
          <div className="text-text-secondary mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            {summary ? <span>{summary}</span> : null}
            <span>
              <b className="text-text font-serif font-medium tabular-nums">{day.exercises.length}</b>{" "}
              exercise{day.exercises.length === 1 ? "" : "s"}
            </span>
            {estMin > 0 ? <span className="tabular-nums">~{estMin} min</span> : null}
            {position?.in_deload ? (
              <span className="text-warning inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-warning)_45%,transparent)] px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                Deload
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col gap-2 md:items-end">
          <Button size="lg" onClick={onStart} disabled={start.isPending} data-testid="start-today-session">
            {start.isPending ? "Starting…" : "Start →"}
          </Button>
          <Link
            href={`/programs/${program.id}/days/${day.id}`}
            className="text-text-secondary hover:text-text text-[13px] font-medium"
          >
            View session →
          </Link>
        </div>
      </div>
      {cycleLabel ? (
        <span className="border-border bg-surface text-text-secondary absolute top-6 right-6 hidden h-[28px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase md:inline-flex">
          {cycleLabel}
        </span>
      ) : null}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-border bg-surface-elevated relative overflow-hidden rounded-[var(--radius-card)] border p-7">
      {children}
    </div>
  );
}

function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
      {children}
    </span>
  );
}
