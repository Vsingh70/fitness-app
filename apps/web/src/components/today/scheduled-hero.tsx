"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useStartScheduled } from "@/lib/hooks/scheduling";
import { useActiveSession } from "@/lib/state/active-session";
import { useCreateEmptySession } from "@/lib/hooks/workouts";
import type { components } from "@/lib/api/types";

type Scheduled = components["schemas"]["ScheduledWorkoutWithDay"];

interface Props {
  scheduled: Scheduled | undefined;
}

export function ScheduledHero({ scheduled }: Props) {
  const router = useRouter();
  const startScheduled = useStartScheduled();
  const createEmpty = useCreateEmptySession();
  const setActive = useActiveSession((s) => s.setActive);

  const onStartEmpty = () => {
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

  const onStartScheduled = () => {
    if (!scheduled) return;
    startScheduled.mutate(scheduled.id, {
      onSuccess: (session) => {
        setActive(session.id, session.started_at);
        router.push(`/workouts/${session.id}`);
      },
    });
  };

  if (!scheduled) {
    return (
      <div className="border-border bg-surface-elevated relative grid gap-6 overflow-hidden rounded-[var(--radius-card)] border p-7 md:grid-cols-[1fr_auto] md:items-end">
        <div className="min-w-0">
          <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.1em]">
            Today
          </span>
          <h2 className="font-serif mt-1.5 text-[28px] font-medium leading-tight tracking-tight md:text-[36px]">
            Rest day
          </h2>
          <p className="text-text-secondary mt-3 max-w-[34rem] text-sm">
            Nothing scheduled. Take it easy or start an empty workout if you&apos;re feeling it.
          </p>
        </div>
        <div className="flex flex-col gap-2 md:items-end">
          <Button size="lg" onClick={onStartEmpty} disabled={createEmpty.isPending}>
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

  const programLabel = scheduled.program_name ?? "Program";
  const dayLabel = scheduled.program_day_name ?? "Day";
  const weekLabel =
    scheduled.mesocycle_week !== null ? `Week ${scheduled.mesocycle_week}` : null;

  return (
    <div className="border-border bg-surface-elevated relative grid gap-6 overflow-hidden rounded-[var(--radius-card)] border p-7 md:grid-cols-[1fr_auto] md:items-end">
      <div className="min-w-0">
        <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.1em]">
          Today · {dayLabel}
        </span>
        <h2 className="font-serif mt-1.5 text-[28px] font-medium leading-tight tracking-tight md:text-[36px]">
          {programLabel}
        </h2>
        <div className="text-text-secondary mt-4 flex flex-wrap gap-4 text-sm">
          <span>
            <b className="text-text font-serif font-medium tabular-nums">
              {scheduled.exercise_count}
            </b>{" "}
            exercises
          </span>
          {scheduled.is_deload ? (
            <span className="text-warning inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-warning)_45%,transparent)] px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em]">
              Deload
            </span>
          ) : null}
        </div>
      </div>
      {weekLabel ? (
        <span className="border-border bg-surface text-text-secondary absolute right-6 top-6 inline-flex h-[28px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold uppercase tracking-[0.08em]">
          {weekLabel}
        </span>
      ) : null}
      <div className="flex flex-col gap-2 md:items-end">
        <Button size="lg" onClick={onStartScheduled} disabled={startScheduled.isPending}>
          {startScheduled.isPending ? "Starting…" : "Start workout →"}
        </Button>
        <Link
          href={`/workouts/calendar`}
          className="text-text-secondary hover:text-text text-[13px] font-medium"
        >
          Reschedule →
        </Link>
      </div>
    </div>
  );
}
