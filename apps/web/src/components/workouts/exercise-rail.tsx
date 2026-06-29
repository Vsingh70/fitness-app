"use client";

import { cn } from "@/lib/cn";
import type { WorkoutExercise } from "@/lib/workouts/types";

interface Props {
  workoutExercises: WorkoutExercise[];
  exerciseNames: Map<string, string>;
  activeId: string | null;
  targetSetsById: Map<string, number | null>;
  onSelect: (workoutExerciseId: string) => void;
}

export function ExerciseRail({
  workoutExercises,
  exerciseNames,
  activeId,
  targetSetsById,
  onSelect,
}: Props) {
  if (workoutExercises.length === 0) return null;

  return (
    <div
      className={cn(
        "border-border bg-bg/[0.86] sticky top-0 z-10 -mx-4 flex gap-2 overflow-x-auto border-b px-4 py-3 backdrop-blur-sm md:-mx-8 md:px-8",
      )}
    >
      {workoutExercises.map((we, idx) => {
        const name = exerciseNames.get(we.exercise_id) ?? "Exercise";
        const target = targetSetsById.get(we.id) ?? null;
        const done = we.sets.length;
        const isActive = we.id === activeId;
        const isComplete = target !== null && target > 0 && done >= target;
        return (
          <button
            key={we.id}
            type="button"
            onClick={() => onSelect(we.id)}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-[var(--radius-pill)] border px-3 py-1.5 text-[13px] transition-colors duration-150 ease-out",
              isActive
                ? "bg-accent text-accent-foreground border-transparent font-semibold"
                : isComplete
                  ? "bg-success-soft text-success border-transparent font-medium"
                  : "border-border bg-surface text-text-secondary hover:text-text",
            )}
          >
            <span className="font-serif text-[11px] tabular-nums opacity-70">
              {String(idx + 1).padStart(2, "0")}
            </span>
            <span className="max-w-[140px] truncate">{name}</span>
            <span className="font-serif text-[11px] tabular-nums opacity-70">
              {done}
              {target !== null ? `/${target}` : ""}
            </span>
          </button>
        );
      })}
    </div>
  );
}
