"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ProgramLibrary } from "@/components/programs/program-library";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMesocycle, useMyPrograms, useProgram } from "@/lib/hooks/programs";
import type { MesocyclePosition, Program, ProgramDay, ProgramListItem } from "@/lib/programs/types";

const DOW = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

/**
 * Active-program "spine": masthead + mesocycle bar, today's session, this week,
 * then the My-programs library. When no program is active but some exist, the
 * library leads so the user can activate one.
 */
export function ActiveProgram() {
  const list = useMyPrograms();

  if (list.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (list.isError) return <p className="text-destructive">Could not load programs.</p>;

  const items = list.data?.items ?? [];
  const active = items.find((p) => p.is_active) ?? null;

  if (!active) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-8">
        <header>
          <h1 className="font-serif text-[32px] font-medium tracking-tight">Programs</h1>
          <p className="text-text-secondary mt-1.5 text-sm">
            No active program — activate one below or browse templates.
          </p>
        </header>
        <ProgramLibrary items={items} />
      </div>
    );
  }

  return <ActiveProgramView active={active} items={items} />;
}

function ActiveProgramView({
  active,
  items,
}: {
  active: ProgramListItem;
  items: ProgramListItem[];
}) {
  const program = useProgram(active.id);
  const meso = useMesocycle(active.id);

  const p = program.data;
  const exerciseIds = useMemo(
    () => (p ? p.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : []),
    [p],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  // Derive a UI-only week view: the program's days are the planned sessions and
  // "today" is the next day in the rotation (first day until scheduling lands).
  const todayIdx = 0;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-9">
      {/* Masthead */}
      <header>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.16em] uppercase">
              Active program
            </span>
            <h1 className="text-text mt-1 font-serif text-[34px] leading-tight font-medium tracking-tight">
              {active.name}
            </h1>
          </div>
          <Link
            href={`/programs/${active.id}`}
            className="border-border-strong text-text-secondary hover:border-text hover:text-text inline-flex h-[34px] shrink-0 items-center rounded-[var(--radius-button)] border px-[14px] text-[13px] font-semibold"
          >
            Edit
          </Link>
        </div>
        <div className="text-text-secondary mt-3 flex flex-wrap gap-x-7 gap-y-1.5 text-[13px]">
          <Meta label="Goal" value={active.goal} capitalize />
          <Meta label="Strategy" value={p ? strategyLabel(p) : "—"} />
          <Meta label="Frequency" value={`${active.days_per_week}×/week`} />
        </div>

        {meso.data ? <MesocycleBar meso={meso.data} /> : null}
      </header>

      {/* Today */}
      {p && p.days.length > 0 ? (
        <TodayCard program={p} day={p.days[todayIdx]!} metaMap={metaMap} />
      ) : null}

      {/* This week */}
      {p && p.days.length > 0 ? (
        <ThisWeek program={p} todayIdx={todayIdx} metaMap={metaMap} />
      ) : null}

      {/* My programs */}
      <ProgramLibrary items={items} />
    </div>
  );
}

function Meta({
  label,
  value,
  capitalize,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
}) {
  return (
    <span>
      <b className={`text-text mr-1.5 font-serif font-medium ${capitalize ? "capitalize" : ""}`}>
        {value}
      </b>
      <span className="text-text-tertiary">{label}</span>
    </span>
  );
}

function strategyLabel(p: Program): string {
  return p.periodization_mode === "continuous" ? "Continuous" : "Periodized block";
}

// Mesocycle bar -------------------------------------------------------------
function MesocycleBar({ meso }: { meso: MesocyclePosition }) {
  if (meso.is_continuous) {
    return (
      <p className="text-text-tertiary mt-5 text-[12px] font-semibold tracking-[0.06em] uppercase">
        Continuous — no scheduled deload
      </p>
    );
  }

  const length = Math.max(1, meso.mesocycle_length_weeks);
  const current = meso.week_in_meso ?? 1;
  const deloadWeek = meso.auto_deload ? length : null;
  const weeks = Array.from({ length }, (_, i) => i + 1);

  return (
    <div className="mt-5 flex flex-col gap-2">
      <div className="flex gap-1.5">
        {weeks.map((w) => {
          const isDeload = w === deloadWeek;
          const state = w < current ? "done" : w === current ? "current" : ("future" as const);
          return (
            <div
              key={w}
              aria-label={`Week ${w}${isDeload ? " (deload)" : ""} — ${state}`}
              className={cellClass(state, isDeload)}
            />
          );
        })}
      </div>
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
        Week {current} of {length}
        {meso.is_deload ? " · deload" : ""}
      </span>
    </div>
  );
}

function cellClass(state: "done" | "current" | "future", isDeload: boolean): string {
  const base = "h-2 flex-1 rounded-[2px]";
  if (isDeload) return `${base} border border-dashed border-[var(--color-accent)]`;
  if (state === "done") return `${base} bg-[var(--color-accent)]`;
  if (state === "current")
    return `${base} border border-[var(--color-accent)] bg-[var(--color-accent-soft)]`;
  return `${base} bg-surface-sunken`;
}

// Today card ----------------------------------------------------------------
function TodayCard({
  program,
  day,
  metaMap,
}: {
  program: Program;
  day: ProgramDay;
  metaMap: Map<string, { name: string; primary_muscle?: string | null }>;
}) {
  const todayDow = DOW[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1];
  const summary = exerciseSummary(day, metaMap);

  return (
    <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-6">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
        Today · {todayDow}
      </span>
      <div className="mt-1.5 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-text font-serif text-[24px] leading-tight font-medium tracking-tight">
            {day.name}
          </h2>
          <p className="text-text-secondary mt-1 text-[13px]">
            {day.exercises.length} exercise{day.exercises.length === 1 ? "" : "s"}
            {summary ? ` · ${summary}` : ""}
          </p>
        </div>
        <Link
          href={`/programs/${program.id}/days/${day.id}`}
          className="bg-accent text-accent-foreground inline-flex h-[42px] items-center rounded-[var(--radius-button)] px-[22px] text-sm font-semibold tracking-[0.01em] hover:brightness-105"
        >
          Start
        </Link>
      </div>
    </div>
  );
}

// This week -----------------------------------------------------------------
function ThisWeek({
  program,
  todayIdx,
  metaMap,
}: {
  program: Program;
  todayIdx: number;
  metaMap: Map<string, { name: string; primary_muscle?: string | null }>;
}) {
  return (
    <section>
      <div className="border-border mb-1 flex items-center justify-between border-b pb-2.5">
        <h2 className="text-text-secondary text-[11px] font-semibold tracking-[0.14em] uppercase">
          This week
        </h2>
        <Link href="/workouts/calendar" className="text-text-tertiary hover:text-text text-xs">
          Full calendar
        </Link>
      </div>
      <div className="flex flex-col">
        {program.days.map((day, idx) => {
          const status: "done" | "today" | "planned" =
            idx < todayIdx ? "done" : idx === todayIdx ? "today" : "planned";
          const summary = exerciseSummary(day, metaMap);
          return (
            <Link
              key={day.id}
              href={`/programs/${program.id}/days/${day.id}`}
              className={`border-border grid grid-cols-[40px_1fr_auto] items-center gap-4 border-b py-3.5 transition-colors ${
                status === "done" ? "opacity-55" : ""
              }`}
            >
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
                {DOW[idx % 7]}
              </span>
              <div className="min-w-0">
                <span className="text-text font-serif text-[16px] font-medium">{day.name}</span>
                {summary ? (
                  <span className="text-text-tertiary ml-2 text-[12px]">{summary}</span>
                ) : null}
              </div>
              <div className="flex items-center gap-4">
                <span className="text-text-tertiary text-[12px] tabular-nums">
                  {day.exercises.length} ex
                </span>
                <StatusLabel status={status} />
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function StatusLabel({ status }: { status: "done" | "today" | "planned" }) {
  if (status === "today") {
    return (
      <span className="text-accent text-[10px] font-semibold tracking-[0.1em] uppercase">
        Today
      </span>
    );
  }
  if (status === "done") {
    return (
      <span className="text-success text-[10px] font-semibold tracking-[0.1em] uppercase">
        Done
      </span>
    );
  }
  return (
    <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
      Planned
    </span>
  );
}

function exerciseSummary(
  day: ProgramDay,
  metaMap: Map<string, { name: string; primary_muscle?: string | null }>,
): string {
  const muscles = new Set<string>();
  for (const ex of day.exercises) {
    const m = metaMap.get(ex.exercise_id)?.primary_muscle;
    if (m) muscles.add(m.replace(/_/g, " "));
  }
  return Array.from(muscles).slice(0, 3).join(" · ");
}
