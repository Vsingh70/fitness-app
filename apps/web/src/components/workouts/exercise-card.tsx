"use client";

import { GripVertical, MoreHorizontal, Trash2 } from "lucide-react";
import { memo, useState, type ReactNode } from "react";

/**
 * Structural interface for drag-grip controls. Uses native PointerEvent so this
 * file does not need to import motion/react (keeps the motion-import budget tight).
 */
export interface GripDragControls {
  start: (event: PointerEvent) => void;
}

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { labelize } from "@/lib/api/exercises";
import { cn } from "@/lib/cn";
import { formatWeight, weightUnitLabel } from "@/lib/utils/format-weight";
import {
  SET_FIELD_LABEL,
  SET_TYPE_LABEL,
  TRACKING_COLUMNS,
  isStructuredSetType,
  sumSegmentReps,
  type SetCreate,
  type TrackingType,
  type WorkoutExercise,
  type WorkoutSet,
} from "@/lib/workouts/types";
import { IntervalSetEditor } from "./interval-set-editor";
import { SegmentEditor } from "./segment-editor";
import { SetRow } from "./set-row";

interface ExerciseCardProps {
  workoutExercise: WorkoutExercise;
  exerciseName: string;
  trackingType: TrackingType;
  previousSets?: WorkoutSet[];
  /** Name of the original exercise when this row is a one-session swap (05 §2). */
  substitutedFor?: string | null;
  /** True when this exercise sits in a non-volume block (warm-up/cooldown, 06 §3c). */
  nonVolume?: boolean;
  /** User's unit system; drives weight display (kg vs lb). */
  unit?: "metric" | "imperial";
  onAddSet: (body: SetCreate) => Promise<void> | void;
  onDeleteSet: (setId: string) => Promise<void> | void;
  onRemoveExercise: () => Promise<void> | void;
  /**
   * Open the in-session divergence menu for this exercise (05): swap for the
   * session, change/swap in the program, remove from the program. Omit to hide
   * (e.g. on a finished session).
   */
  onMoreActions?: () => void;
  onSetCommitted?: () => void;
  /** Optional block control (warm-up/working/cooldown), rendered in the header. */
  blockControl?: ReactNode;
  /**
   * When provided, renders a drag-grip handle in the card header so the user
   * can reorder the exercise within its block. Omit on finished/read-only views.
   */
  dragControls?: GripDragControls;
}

/** Set-entry modes the card can be in. */
type EntryMode = "straight" | "structured" | "interval";

function summarize(set: WorkoutSet, tracking: TrackingType, unit?: "metric" | "imperial"): string {
  const cols = TRACKING_COLUMNS[tracking];
  const parts: string[] = [];
  for (const c of cols) {
    const value = set[c as keyof WorkoutSet];
    if (value === null || value === undefined) continue;
    if (c === "weight_kg") {
      parts.push(formatWeight(value as string | number, unit));
    } else {
      parts.push(`${value}${c === "duration_seconds" ? "s" : c === "distance_meters" ? "m" : ""}`);
    }
  }
  return parts.join(" x ");
}

/** A logged structured/interval set rendered as a read-only summary chip. */
function StructuredSetSummary({
  set,
  index,
  unit,
  onDelete,
}: {
  set: WorkoutSet;
  index: number;
  unit?: "metric" | "imperial";
  onDelete?: () => void;
}) {
  const isInterval = set.set_type === "interval";
  const detail = isInterval
    ? (() => {
        const work = set.segments.find((s) => s.kind === "work");
        const rest = set.segments.find((s) => s.kind === "rest");
        return `${set.rounds ?? "?"}× ${work?.duration_seconds ?? "?"}s work${
          rest ? ` / ${rest.duration_seconds}s rest` : ""
        }`;
      })()
    : (() => {
        const bouts = set.segments.filter((s) => s.kind === "mini_set");
        const total = sumSegmentReps(bouts);
        return `${bouts.map((b) => b.reps ?? 0).join("+")} = ${total} reps${
          set.weight_kg ? ` @ ${formatWeight(set.weight_kg, unit)}` : ""
        }`;
      })();

  return (
    <div
      data-testid="structured-set"
      className={cn(
        "flex items-center gap-2 rounded-[var(--radius-button)] px-2 py-2 text-sm",
        set.is_pr ? "bg-pr-soft" : "bg-surface",
        set.id.startsWith("tmp-") ? "opacity-60" : "",
      )}
    >
      <span className="text-text-secondary font-serif text-[15px] tabular-nums">{index + 1}</span>
      <span className="border-border-strong text-text-secondary inline-flex h-[20px] items-center rounded-[var(--radius-pill)] border px-2 text-[10px] font-semibold tracking-[0.08em] uppercase">
        {SET_TYPE_LABEL[set.set_type]}
      </span>
      <span className="text-text min-w-0 flex-1 truncate font-serif text-[15px] tabular-nums">
        {detail}
      </span>
      {set.is_pr ? (
        <span className="text-pr text-[10px] font-semibold tracking-[0.1em] uppercase">PR</span>
      ) : null}
      {onDelete ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          aria-label={`Delete set ${index + 1}`}
          onClick={onDelete}
        >
          ×
        </Button>
      ) : null}
    </div>
  );
}

export const ExerciseCard = memo(function ExerciseCard({
  workoutExercise,
  exerciseName,
  trackingType,
  previousSets,
  substitutedFor,
  nonVolume = false,
  unit,
  onAddSet,
  onDeleteSet,
  onRemoveExercise,
  onMoreActions,
  onSetCommitted,
  blockControl,
  dragControls,
}: ExerciseCardProps) {
  const [showAdd, setShowAdd] = useState(workoutExercise.sets.length === 0);
  const [entryMode, setEntryMode] = useState<EntryMode>("straight");
  const columns = TRACKING_COLUMNS[trackingType];

  const submitStructured = async (body: SetCreate) => {
    await onAddSet(body);
    onSetCommitted?.();
    setEntryMode("straight");
    setShowAdd(false);
  };

  return (
    <Card data-workout-exercise-id={workoutExercise.id}>
      <CardHeader>
        <div className="flex min-w-0 items-center gap-2">
          {dragControls ? (
            <span
              role="button"
              aria-label={`Drag to reorder ${exerciseName}`}
              tabIndex={-1}
              style={{ cursor: "grab", touchAction: "none" }}
              onPointerDown={(e) => dragControls.start(e.nativeEvent)}
              className="text-text-tertiary shrink-0"
            >
              <GripVertical className="h-4 w-4" />
            </span>
          ) : null}
          <div className="flex min-w-0 flex-col gap-1 tracking-normal normal-case">
            <div className="flex items-center gap-3">
              <h3 className="text-text font-serif text-xl font-medium tracking-tight">
                {exerciseName}
              </h3>
              <span className="border-border-strong text-text-secondary inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                {labelize(trackingType)}
              </span>
              {nonVolume ? (
                <span className="border-border text-text-tertiary inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-dashed px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                  No volume
                </span>
              ) : null}
            </div>
            {substitutedFor ? (
              <span className="text-text-tertiary text-xs">in place of {substitutedFor}</span>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {blockControl}
          {onMoreActions ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`More actions for ${exerciseName}`}
              data-testid="exercise-more-actions"
              onClick={() => onMoreActions()}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Remove ${exerciseName}`}
              onClick={() => void onRemoveExercise()}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        <div
          className={cn(
            "text-text-tertiary grid items-center gap-2 px-2 text-[10px] font-semibold tracking-[0.1em] uppercase",
          )}
          style={{
            gridTemplateColumns: `2rem 6rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
          }}
        >
          <span>Set</span>
          <span>Previous</span>
          {columns.map((c) => (
            <span key={c}>{c === "weight_kg" ? weightUnitLabel(unit) : SET_FIELD_LABEL[c]}</span>
          ))}
          <span></span>
        </div>
        {workoutExercise.sets.map((s, idx) =>
          isStructuredSetType(s.set_type) || s.set_type === "interval" ? (
            <StructuredSetSummary
              key={s.id}
              set={s}
              index={idx}
              unit={unit}
              onDelete={() => void onDeleteSet(s.id)}
            />
          ) : (
            <SetRow
              key={s.id}
              trackingType={trackingType}
              setIndex={idx}
              unit={unit}
              initial={Object.fromEntries(
                columns
                  .map((c) => [
                    c,
                    s[c as keyof WorkoutSet] != null ? String(s[c as keyof WorkoutSet]) : "",
                  ])
                  .filter(([, v]) => v !== ""),
              )}
              previousSummary={
                previousSets?.[idx] ? summarize(previousSets[idx]!, trackingType, unit) : undefined
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
          ),
        )}

        {entryMode === "structured" ? (
          <SegmentEditor
            defaultWeightKg={null}
            unit={unit}
            onSubmit={submitStructured}
            onCancel={() => setEntryMode("straight")}
          />
        ) : entryMode === "interval" ? (
          <IntervalSetEditor
            onSubmit={submitStructured}
            onCancel={() => setEntryMode("straight")}
          />
        ) : showAdd ? (
          <SetRow
            key={`new-${workoutExercise.sets.length}`}
            trackingType={trackingType}
            setIndex={workoutExercise.sets.length}
            unit={unit}
            previousSummary={
              previousSets?.[workoutExercise.sets.length]
                ? summarize(previousSets[workoutExercise.sets.length]!, trackingType, unit)
                : undefined
            }
            onSubmit={async (body) => {
              await onAddSet(body);
              onSetCommitted?.();
              setShowAdd(true);
            }}
          />
        ) : null}

        {entryMode === "straight" ? (
          <div className="flex flex-wrap items-center gap-1 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowAdd(true)}>
              + Add set
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setEntryMode("structured")}
            >
              + Rest-pause / cluster
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setEntryMode("interval")}
            >
              + Interval
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
});
