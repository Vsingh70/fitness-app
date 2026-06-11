"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useProgram } from "@/lib/hooks/programs";
import type { IntensityMode, ProgramDayExercise } from "@/lib/programs/types";

const STRATEGY_LABELS: Record<string, string> = {
  linear: "Linear",
  double_progression: "Double progression",
  rpe_based: "RPE-based",
  none: "No auto-progression",
};

export default function ProgramDayPage() {
  const { id, dayId } = useParams<{ id: string; dayId: string }>();
  const program = useProgram(id);

  const p = program.data;
  const day = p?.days.find((d) => d.id === dayId) ?? null;
  const dayNumber = p ? p.days.findIndex((d) => d.id === dayId) + 1 : 0;

  const exerciseIds = useMemo(() => (day ? day.exercises.map((e) => e.exercise_id) : []), [day]);
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  if (program.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (program.isError || !p) return <p className="text-destructive">Could not load program.</p>;
  if (!day) return <p className="text-text-secondary">Day not found.</p>;

  const intensityLabel = intensityHeader(p.intensity_mode);
  const workingSets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(workingSets * 2.5);
  const muscles = Array.from(
    new Set(
      day.exercises
        .map((ex) => metaMap.get(ex.exercise_id)?.primary_muscle as string | undefined)
        .filter((m): m is string => Boolean(m)),
    ),
  );
  const metaBits = [
    `${day.exercises.length} exercises`,
    `${workingSets} working sets`,
    `~${estMin} min`,
    ...(muscles.length ? [muscles.map(titleCase).join(" · ")] : []),
  ];

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      {/* Top chrome: breadcrumb + Start workout */}
      <div className="mb-5 flex items-center justify-between gap-4">
        <p className="text-text-tertiary text-xs">
          <Link href={`/programs/${p.id}`} className="hover:text-text">
            {p.name}
          </Link>{" "}
          ›
        </p>
        <Button type="button" size="sm">
          Start workout
        </Button>
      </div>

      {/* Hero */}
      <div className="border-text border-b-2 pb-3.5">
        <div className="text-accent text-[11px] font-semibold tracking-[0.14em] uppercase">
          Day {dayNumber} · <span className="capitalize">{p.goal.replace(/_/g, " ")}</span>
        </div>
        <h1 className="mt-1.5 font-serif text-[32px] leading-tight font-medium tracking-[-0.02em]">
          {day.name}
        </h1>
        <div className="text-text-secondary mt-2 text-[13px]">{metaBits.join(" · ")}</div>
      </div>

      {/* Exercise scheme blocks */}
      <div className="flex flex-col">
        {day.exercises.map((ex, i) => (
          <ExerciseBlock
            key={ex.id}
            index={i}
            ex={ex}
            name={metaMap.get(ex.exercise_id)?.name ?? "Exercise"}
            muscle={metaMap.get(ex.exercise_id)?.primary_muscle as string | undefined}
            intensityMode={p.intensity_mode}
            intensityLabel={intensityLabel}
          />
        ))}
      </div>
    </div>
  );
}

function ExerciseBlock({
  index,
  ex,
  name,
  muscle,
  intensityMode,
  intensityLabel,
}: {
  index: number;
  ex: ProgramDayExercise;
  name: string;
  muscle?: string;
  intensityMode: IntensityMode;
  intensityLabel: string | null;
}) {
  const cells: { label: string; value: string }[] = [
    { label: "Sets", value: String(ex.target_sets) },
    { label: "Reps", value: repsDisplay(ex) },
    ...(intensityLabel
      ? [{ label: intensityLabel, value: intensityDisplay(ex, intensityMode) }]
      : []),
    { label: "Rest", value: ex.rest_seconds ? formatRest(ex.rest_seconds) : "—" },
  ];

  return (
    <div className="border-border border-b py-4">
      <div className="flex items-baseline gap-3">
        <span className="text-text-tertiary w-[22px] font-serif text-[13px] tabular-nums">
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className="font-serif text-[19px]">{name}</span>
        {muscle ? (
          <span className="text-text-tertiary ml-auto text-[10px] font-semibold tracking-[0.08em] uppercase">
            {titleCase(muscle)}
          </span>
        ) : null}
      </div>
      <div className="mt-2.5 ml-[34px] flex gap-[22px]">
        {cells.map((c) => (
          <div key={c.label}>
            <div className="font-serif text-[17px] tabular-nums">{c.value}</div>
            <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
              {c.label}
            </div>
          </div>
        ))}
      </div>
      <div className="text-text-secondary mt-2.5 ml-[34px] text-[12px]">
        Progression —{" "}
        <b className="text-accent font-semibold">
          {STRATEGY_LABELS[ex.progression_strategy] ?? ex.progression_strategy}
        </b>
      </div>
    </div>
  );
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatRest(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, "0")}` : `${s}s`;
}

function intensityHeader(mode: IntensityMode): string | null {
  if (mode === "rpe") return "RPE";
  if (mode === "rir") return "RIR";
  return null;
}

function repsDisplay(ex: ProgramDayExercise): string {
  const low = ex.target_reps_low;
  const high = ex.target_reps_high;
  if (low == null) return "—";
  if (ex.rep_mode === "target" || high == null || high === low) return String(low);
  return `${low}–${high}`;
}

function intensityDisplay(ex: ProgramDayExercise, mode: IntensityMode): string {
  if (mode === "off") return "—";
  const low = mode === "rpe" ? ex.target_rpe_low : ex.target_rir_low;
  const high = mode === "rpe" ? ex.target_rpe_high : ex.target_rir_high;
  if (low == null) return "—";
  const lowStr = String(low);
  const highStr = high == null ? null : String(high);
  if (highStr == null || highStr === lowStr) return lowStr;
  return `${lowStr}–${highStr}`;
}
