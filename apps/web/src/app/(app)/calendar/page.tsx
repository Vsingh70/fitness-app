"use client";

import Link from "next/link";
import { useMemo } from "react";

import { exerciseSummary, type ExMetaMap } from "@/components/programs/day-meta";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { Card, CardContent } from "@/components/ui/card";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMe } from "@/lib/hooks/me";
import { useMyPrograms, usePosition, useProgram } from "@/lib/hooks/programs";
import { useSessionHistory } from "@/lib/hooks/workouts";
import { groupByCycle, projectRotation, type ProjectedCycle } from "@/lib/programs/rotation";
import type { Program, ProgramListItem } from "@/lib/programs/types";
import type { WorkoutSessionListItem } from "@/lib/workouts/types";

// How far to project the rotation forward. Two mesocycles of a 7-slot microcycle
// plus headroom — enough to show the upcoming deload without an unbounded list.
const PROJECTION_COUNT = 24;

export default function CalendarPage() {
  const list = useMyPrograms();
  const items = list.data?.items ?? [];
  const active = items.find((p) => p.is_active) ?? null;

  return (
    <RevealGroup className="page-shell flex flex-col" style={{ gap: "var(--space-section)" }}>
      <RevealItem>
        <header className="flex items-end justify-between gap-4">
          <div>
            <h1
              className="font-serif font-medium tracking-tight"
              style={{ fontSize: "var(--text-h2)" }}
            >
              Calendar
            </h1>
            <p className="text-text-secondary mt-1.5 text-sm">
              Your training projected forward through the rotation, and what you’ve recently done.
            </p>
          </div>
          <Link
            href="/workouts"
            className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] shrink-0 items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase"
          >
            Workouts
          </Link>
        </header>
      </RevealItem>

      {list.isLoading ? (
        <RevealItem>
          <p className="text-text-secondary">Loading…</p>
        </RevealItem>
      ) : list.isError ? (
        <RevealItem>
          <p className="text-destructive">Could not load programs.</p>
        </RevealItem>
      ) : active ? (
        <UpcomingForActive active={active} />
      ) : (
        <RevealItem>
          <NoActiveProgram hasPrograms={items.length > 0} />
        </RevealItem>
      )}

      <RevealItem>
        <RecentSessions />
      </RevealItem>
    </RevealGroup>
  );
}

function NoActiveProgram({ hasPrograms }: { hasPrograms: boolean }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <h2 className="font-serif text-lg font-medium tracking-tight">No active program</h2>
        <p className="text-text-secondary text-sm">
          The calendar projects the rotation of your active program. Activate one to see your
          upcoming sessions laid out in order.
        </p>
        <div>
          <Link
            href="/programs"
            className="bg-accent text-accent-foreground inline-flex h-[40px] items-center rounded-[var(--radius-button)] px-4 text-sm font-semibold hover:brightness-105"
          >
            {hasPrograms ? "Choose a program" : "Browse programs"}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Loads the active program + its rotation position, then projects the rotation
 * forward. Kept as a child so the position/program queries only fire once an
 * active program is known.
 */
function UpcomingForActive({ active }: { active: ProgramListItem }) {
  const program = useProgram(active.id);
  const position = usePosition(active.id);
  const p = program.data;
  const pos = position.data;

  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  const cycles = useMemo<ProjectedCycle[]>(() => {
    if (!p || !pos) return [];
    const projected = projectRotation(p, pos, PROJECTION_COUNT);
    return groupByCycle(projected, pos.mesocycle_length_microcycles);
  }, [p, pos]);

  if (program.isLoading || position.isLoading) {
    return (
      <RevealItem>
        <p className="text-text-secondary">Loading…</p>
      </RevealItem>
    );
  }
  if (!p || !pos) {
    return (
      <RevealItem>
        <p className="text-destructive">Could not load the active program.</p>
      </RevealItem>
    );
  }

  if (cycles.length === 0) {
    return (
      <RevealItem>
        <Card>
          <CardContent className="flex flex-col gap-2">
            <h2 className="font-serif text-lg font-medium tracking-tight">{p.name}</h2>
            <p className="text-text-secondary text-sm">
              This program has no training slots yet, so there’s no rotation to project.{" "}
              <Link href={`/programs/${p.id}/edit`} className="text-accent hover:underline">
                Add slots
              </Link>{" "}
              to get started.
            </p>
          </CardContent>
        </Card>
      </RevealItem>
    );
  }

  return (
    <RevealItem>
      <section aria-label="Upcoming sessions">
        <h2 className="text-text-secondary mb-1 text-[13px] font-semibold tracking-[0.1em] uppercase">
          Upcoming
        </h2>
        <p className="text-text-tertiary mb-4 text-xs">
          {p.name} · timing is pure rotation, advanced each time you train (no fixed dates).
        </p>
        <div className="flex flex-col gap-5">
          {cycles.map((cycle) => (
            <CycleGroup key={cycle.key} cycle={cycle} program={p} metaMap={metaMap} />
          ))}
        </div>
      </section>
    </RevealItem>
  );
}

function CycleGroup({
  cycle,
  program,
  metaMap,
}: {
  cycle: ProjectedCycle;
  program: Program;
  metaMap: ExMetaMap;
}) {
  const label = cycle.isDeload
    ? "Deload microcycle"
    : `Cycle ${cycle.repetition} of ${cycle.mesocycleLength}`;

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
          {label}
        </h3>
        {cycle.isDeload ? (
          <span className="text-text-tertiary border-border-strong inline-flex h-[18px] items-center rounded-[var(--radius-pill)] border border-dashed px-2 text-[9px] font-semibold tracking-[0.12em] uppercase">
            Lighter week
          </span>
        ) : null}
      </div>
      <ul className="flex flex-col gap-2">
        {cycle.slots.map((item) => {
          const summary = exerciseSummary(item.slot, metaMap);
          const restProgram = item.slot.is_rest_day;
          const trainable = !restProgram && item.slot.exercises.length > 0;
          const inner = (
            <>
              <span
                className={`font-serif text-sm tabular-nums ${
                  item.isCurrent ? "text-text font-semibold" : "text-text-tertiary"
                }`}
              >
                {item.isCurrent ? "Now" : item.ordinal}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-text flex items-center gap-2">
                  <span className="truncate font-medium">{item.slot.name}</span>
                  {item.isCurrent ? (
                    <span className="text-accent inline-flex h-[20px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] px-[8px] text-[10px] font-semibold tracking-[0.08em] uppercase">
                      Today
                    </span>
                  ) : null}
                </div>
                <div className="text-text-tertiary text-xs">
                  {restProgram
                    ? "Rest day"
                    : summary
                      ? `${summary} · ${item.slot.exercises.length} ex`
                      : `${item.slot.exercises.length} exercise${item.slot.exercises.length === 1 ? "" : "s"}`}
                </div>
              </div>
            </>
          );

          const className = `border-border flex items-center gap-3 rounded-[var(--radius-button)] border px-3 py-2 ${
            item.isCurrent ? "bg-accent-soft border-accent/40" : "bg-surface-elevated"
          } ${restProgram ? "italic" : ""}`;

          return (
            <li key={item.key}>
              {trainable ? (
                <Link
                  href={`/programs/${program.id}/days/${item.slot.id}`}
                  className={`${className} hover:bg-surface`}
                >
                  {inner}
                </Link>
              ) : (
                <div className={className}>{inner}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function RecentSessions() {
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";
  const history = useSessionHistory(15);
  const items = useMemo<WorkoutSessionListItem[]>(
    () => history.data?.pages.flatMap((p) => p.items) ?? [],
    [history.data],
  );
  const completed = items.filter((s) => !!s.ended_at);

  return (
    <section aria-label="Recent sessions">
      <h2 className="text-text-secondary mb-3 text-[13px] font-semibold tracking-[0.1em] uppercase">
        Recently completed
      </h2>
      {history.isLoading ? (
        <p className="text-text-secondary">Loading…</p>
      ) : history.isError ? (
        <p className="text-destructive">Could not load sessions.</p>
      ) : completed.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-text-secondary text-sm">
              No completed sessions yet. Finished workouts show up here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <ul className="flex flex-col gap-2">
          {completed.slice(0, 12).map((item) => (
            <li key={item.id}>
              <Link
                href={`/workouts/${item.id}`}
                className="hover:bg-surface border-border bg-surface-elevated flex items-center justify-between gap-3 rounded-[var(--radius-button)] border px-3 py-2"
              >
                <div className="flex min-w-0 flex-col">
                  <span className="text-text truncate font-medium">
                    {item.name ?? "Untitled session"}
                  </span>
                  <span className="text-text-tertiary text-xs">
                    {new Date(item.started_at).toLocaleString(undefined, {
                      timeZone: timezone,
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>
                {item.ended_at ? (
                  <span className="text-success bg-success-soft border-success/40 inline-flex h-[22px] shrink-0 items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                    Done
                  </span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
