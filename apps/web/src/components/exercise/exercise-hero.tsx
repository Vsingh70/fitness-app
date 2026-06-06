"use client";

import { cn } from "@/lib/cn";
import type { components } from "@/lib/api/types";

type ExerciseSummary = components["schemas"]["ExerciseSummaryResponse"];

interface Props {
  exercise: ExerciseSummary;
}

const MOVEMENT_LABEL: Record<components["schemas"]["MovementPattern"], string> = {
  squat: "Compound",
  hinge: "Compound",
  horizontal_push: "Compound",
  vertical_push: "Compound",
  horizontal_pull: "Compound",
  vertical_pull: "Compound",
  lunge: "Compound",
  carry: "Carry",
  rotation: "Rotation",
  anti_rotation: "Anti-rotation",
  isolation: "Isolation",
  cardio: "Cardio",
};

function muscleLabel(muscle: string): string {
  return muscle.replace(/_/g, " ");
}

function equipmentLabel(equipment: string): string {
  return equipment.replace(/_/g, " ");
}

export function ExerciseHero({ exercise }: Props) {
  const kicker = `${MOVEMENT_LABEL[exercise.movement_pattern]} · ${equipmentLabel(exercise.equipment)}`;
  return (
    <div
      className="border-border bg-surface relative overflow-hidden rounded-[var(--radius-card)] border px-6 py-6"
      style={{
        backgroundImage:
          "radial-gradient(700px 280px at 100% 0%, var(--color-accent-soft), transparent 65%)",
      }}
    >
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
        {kicker}
      </span>
      <h1 className="mt-1 font-serif text-[28px] leading-tight font-medium tracking-tight md:text-[32px]">
        {exercise.name}
      </h1>
      <div className="mt-3 flex flex-wrap gap-2">
        <MuscleChip muscle={muscleLabel(exercise.primary_muscle)} primary />
        {exercise.secondary_muscles.map((m) => (
          <MuscleChip key={m} muscle={muscleLabel(m)} />
        ))}
      </div>
    </div>
  );
}

function MuscleChip({ muscle, primary }: { muscle: string; primary?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase",
        primary
          ? "text-accent border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)]"
          : "border-border-strong text-text-secondary",
      )}
    >
      {muscle}
    </span>
  );
}
