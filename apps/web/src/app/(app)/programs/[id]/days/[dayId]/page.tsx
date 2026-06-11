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

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-7">
      {/* Hero */}
      <header>
        <p className="text-text-tertiary text-xs">
          <Link href="/programs" className="hover:text-text">
            {p.name}
          </Link>{" "}
          ›
        </p>
        <span className="text-text-tertiary mt-1 block text-[11px] font-semibold tracking-[0.14em] uppercase">
          Day {dayNumber} · {p.goal}
          {p.periodization_mode === "continuous" ? "" : ` · ${p.weeks}-week block`}
        </span>
        <h1 className="text-text mt-1 font-serif text-[32px] leading-tight font-medium tracking-tight">
          {day.name}
        </h1>
      </header>

      {/* Scheme table header */}
      <div className="text-text-tertiary grid grid-cols-[1fr_repeat(4,56px)] gap-3 text-[10px] font-semibold tracking-[0.08em] uppercase">
        <span>Exercise</span>
        <span className="text-right">Sets</span>
        <span className="text-right">Reps</span>
        <span className="text-right">{intensityLabel ?? "—"}</span>
        <span className="text-right">Rest</span>
      </div>

      <div className="flex flex-col">
        {day.exercises.map((ex) => (
          <ExerciseRow
            key={ex.id}
            ex={ex}
            name={metaMap.get(ex.exercise_id)?.name ?? "Exercise"}
            intensityMode={p.intensity_mode}
          />
        ))}
      </div>

      <Button type="button" size="lg" className="self-start">
        Start workout
      </Button>
    </div>
  );
}

function ExerciseRow({
  ex,
  name,
  intensityMode,
}: {
  ex: ProgramDayExercise;
  name: string;
  intensityMode: IntensityMode;
}) {
  return (
    <div className="border-border flex flex-col gap-1.5 border-b py-3.5">
      <div className="grid grid-cols-[1fr_repeat(4,56px)] items-center gap-3">
        <span className="text-text font-serif text-[16px] font-medium">{name}</span>
        <span className="text-text-secondary text-right text-[13px] tabular-nums">
          {ex.target_sets}
        </span>
        <span className="text-text-secondary text-right text-[13px] tabular-nums">
          {repsDisplay(ex)}
        </span>
        <span className="text-text-secondary text-right text-[13px] tabular-nums">
          {intensityDisplay(ex, intensityMode)}
        </span>
        <span className="text-text-secondary text-right text-[13px] tabular-nums">
          {ex.rest_seconds ? `${ex.rest_seconds}s` : "—"}
        </span>
      </div>
      <span className="text-text-tertiary text-[11px]">
        Progression — {STRATEGY_LABELS[ex.progression_strategy] ?? ex.progression_strategy}
      </span>
    </div>
  );
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
