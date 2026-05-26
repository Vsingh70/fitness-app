"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import {
  SET_FIELD_LABEL,
  TRACKING_COLUMNS,
  type SetCreate,
  type TrackingType,
  type WorkoutExercise,
  type WorkoutSet,
} from "@/lib/workouts/types";
import { SetRow } from "./set-row";

interface ExerciseCardProps {
  workoutExercise: WorkoutExercise;
  exerciseName: string;
  trackingType: TrackingType;
  previousSets?: WorkoutSet[];
  onAddSet: (body: SetCreate) => Promise<void> | void;
  onDeleteSet: (setId: string) => Promise<void> | void;
  onRemoveExercise: () => Promise<void> | void;
  onSetCommitted?: () => void;
}

function summarize(set: WorkoutSet, tracking: TrackingType): string {
  const cols = TRACKING_COLUMNS[tracking];
  const parts: string[] = [];
  for (const c of cols) {
    const value = set[c as keyof WorkoutSet];
    if (value === null || value === undefined) continue;
    parts.push(
      `${value}${c === "weight_kg" ? "kg" : c === "duration_seconds" ? "s" : c === "distance_meters" ? "m" : ""}`,
    );
  }
  return parts.join(" x ");
}

export function ExerciseCard({
  workoutExercise,
  exerciseName,
  trackingType,
  previousSets,
  onAddSet,
  onDeleteSet,
  onRemoveExercise,
  onSetCommitted,
}: ExerciseCardProps) {
  const [showAdd, setShowAdd] = useState(workoutExercise.sets.length === 0);
  const columns = TRACKING_COLUMNS[trackingType];

  return (
    <Card data-workout-exercise-id={workoutExercise.id}>
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">{exerciseName}</h3>
          <span className="text-text-tertiary text-xs">{trackingType}</span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-label={`Remove ${exerciseName}`}
          onClick={() => void onRemoveExercise()}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        <div
          className={cn("text-text-tertiary grid items-center gap-2 px-2 text-xs uppercase")}
          style={{
            gridTemplateColumns: `2rem 6rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
          }}
        >
          <span>Set</span>
          <span>Previous</span>
          {columns.map((c) => (
            <span key={c}>{SET_FIELD_LABEL[c]}</span>
          ))}
          <span></span>
        </div>
        {workoutExercise.sets.map((s, idx) => (
          <SetRow
            key={s.id}
            trackingType={trackingType}
            setIndex={idx}
            initial={Object.fromEntries(
              columns
                .map((c) => [
                  c,
                  s[c as keyof WorkoutSet] != null ? String(s[c as keyof WorkoutSet]) : "",
                ])
                .filter(([, v]) => v !== ""),
            )}
            previousSummary={
              previousSets?.[idx] ? summarize(previousSets[idx]!, trackingType) : undefined
            }
            isPr={s.is_pr ?? false}
            isPending={s.id.startsWith("tmp-")}
            onSubmit={async (body) => {
              // For now updates require a separate hook; the card focuses on add.
              await onAddSet(body);
              onSetCommitted?.();
            }}
            onDelete={() => void onDeleteSet(s.id)}
          />
        ))}
        {showAdd ? (
          <SetRow
            key={`new-${workoutExercise.sets.length}`}
            trackingType={trackingType}
            setIndex={workoutExercise.sets.length}
            previousSummary={
              previousSets?.[workoutExercise.sets.length]
                ? summarize(previousSets[workoutExercise.sets.length]!, trackingType)
                : undefined
            }
            onSubmit={async (body) => {
              await onAddSet(body);
              onSetCommitted?.();
              setShowAdd(true);
            }}
          />
        ) : null}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="self-start"
          onClick={() => setShowAdd(true)}
        >
          + Add set
        </Button>
      </CardContent>
    </Card>
  );
}
