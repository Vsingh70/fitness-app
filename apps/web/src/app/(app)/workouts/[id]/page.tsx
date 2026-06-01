"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ExerciseCard } from "@/components/workouts/exercise-card";
import { ExercisePicker } from "@/components/workouts/exercise-picker";
import { ExerciseRail } from "@/components/workouts/exercise-rail";
import { FloatingRestBar } from "@/components/workouts/floating-rest-bar";
import {
  KeyboardShortcuts,
  KeyboardShortcutsSheet,
} from "@/components/workouts/keyboard-shortcuts";
import { NextUpPreview } from "@/components/workouts/next-up-preview";
import { PlateMathStrip } from "@/components/workouts/plate-math";
import { ReadOnlySessionView } from "@/components/workouts/read-only-session";
import { SessionTimer } from "@/components/workouts/session-timer";
import { searchExercises } from "@/lib/api/workouts";
import {
  useAddExercise,
  useAddSet,
  useDeleteSet,
  useFinishSession,
  useRemoveExercise,
  useSession,
} from "@/lib/hooks/workouts";
import { useActiveSession } from "@/lib/state/active-session";
import type { Exercise, WorkoutExercise } from "@/lib/workouts/types";

const DEFAULT_REST_SECONDS = 90;

function lastWeightKg(we: WorkoutExercise): number | null {
  for (let i = we.sets.length - 1; i >= 0; i -= 1) {
    const w = we.sets[i]!.weight_kg;
    if (w !== null && w !== undefined) {
      const n = typeof w === "number" ? w : Number(w);
      if (Number.isFinite(n) && n > 0) return n;
    }
  }
  return null;
}

export default function WorkoutDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const session = useSession(id);
  const setActive = useActiveSession((s) => s.setActive);
  const clearActive = useActiveSession((s) => s.clearActive);

  const addExercise = useAddExercise(id);
  const addSet = useAddSet(id);
  const deleteSet = useDeleteSet(id);
  const removeExercise = useRemoveExercise(id);
  const finishSession = useFinishSession(id);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeWorkoutExerciseId, setActiveWorkoutExerciseId] = useState<string | null>(null);
  const [restKey, setRestKey] = useState<number | null>(null);
  const [restTotal, setRestTotal] = useState(DEFAULT_REST_SECONDS);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    if (session.data && !session.data.ended_at) {
      setActive(session.data.id, session.data.started_at);
    }
  }, [session.data, setActive]);

  const exerciseIds = useMemo(
    () => (session.data ? session.data.workout_exercises.map((we) => we.exercise_id) : []),
    [session.data],
  );

  const exercisesQuery = useQuery({
    queryKey: ["exercise-meta", [...exerciseIds].sort().join(",")],
    queryFn: async () => {
      if (exerciseIds.length === 0) return new Map<string, Exercise>();
      const list = await searchExercises(undefined, { limit: 200 });
      const map = new Map<string, Exercise>();
      for (const ex of list.items) if (exerciseIds.includes(ex.id)) map.set(ex.id, ex);
      return map;
    },
    enabled: exerciseIds.length > 0,
    staleTime: 60_000,
  });

  // Keep activeWorkoutExerciseId in sync with the session's exercises.
  useEffect(() => {
    const wes = session.data?.workout_exercises ?? [];
    if (wes.length === 0) {
      if (activeWorkoutExerciseId !== null) setActiveWorkoutExerciseId(null);
      return;
    }
    if (activeWorkoutExerciseId && wes.some((we) => we.id === activeWorkoutExerciseId)) return;
    setActiveWorkoutExerciseId(wes[0]!.id);
  }, [session.data?.workout_exercises, activeWorkoutExerciseId]);

  const scrollToExercise = useCallback((workoutExerciseId: string) => {
    if (typeof document === "undefined") return;
    const target = document.querySelector<HTMLElement>(
      `[data-workout-exercise-id="${workoutExerciseId}"]`,
    );
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const selectExercise = useCallback(
    (workoutExerciseId: string) => {
      setActiveWorkoutExerciseId(workoutExerciseId);
      scrollToExercise(workoutExerciseId);
    },
    [scrollToExercise],
  );

  if (session.isLoading) return <p className="text-text-secondary">Loading session…</p>;
  if (session.isError) return <p className="text-destructive">Could not load session.</p>;
  if (!session.data) return null;

  const s = session.data;
  const isFinished = !!s.ended_at;
  const showReadOnly = isFinished && !editMode;

  const onFinish = () => {
    finishSession.mutate(undefined, {
      onSuccess: () => {
        clearActive();
        router.push(`/workouts/${s.id}/summary`);
      },
    });
  };

  const targetSetsById = new Map<string, number | null>();
  const exerciseNames = new Map<string, string>();
  for (const we of s.workout_exercises) {
    targetSetsById.set(we.id, null);
    exerciseNames.set(we.exercise_id, exercisesQuery.data?.get(we.exercise_id)?.name ?? "Exercise");
  }

  const activeIdx = activeWorkoutExerciseId
    ? s.workout_exercises.findIndex((we) => we.id === activeWorkoutExerciseId)
    : -1;
  const activeWe = activeIdx >= 0 ? s.workout_exercises[activeIdx] : null;
  const nextWe = activeIdx >= 0 ? s.workout_exercises[activeIdx + 1] : null;

  const nextExercise = () => {
    if (s.workout_exercises.length === 0) return;
    const i = activeIdx >= 0 ? activeIdx : 0;
    const j = Math.min(s.workout_exercises.length - 1, i + 1);
    selectExercise(s.workout_exercises[j]!.id);
  };
  const prevExercise = () => {
    if (s.workout_exercises.length === 0) return;
    const i = activeIdx >= 0 ? activeIdx : 0;
    const j = Math.max(0, i - 1);
    selectExercise(s.workout_exercises[j]!.id);
  };
  const toggleRest = () => {
    if (restKey === null) setRestKey(Date.now());
    else setRestKey(null);
  };

  // Plate math only for barbell weight_reps exercises with a previous weight.
  const activeExerciseMeta = activeWe ? exercisesQuery.data?.get(activeWe.exercise_id) : undefined;
  const plateTargetKg =
    activeWe && activeExerciseMeta?.equipment === "barbell" && activeExerciseMeta.tracking_type === "weight_reps"
      ? lastWeightKg(activeWe)
      : null;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 pb-32">
      {!showReadOnly ? (
        <KeyboardShortcuts
          onAddExercise={() => setPickerOpen(true)}
          onShowHelp={() => setShortcutsOpen(true)}
          onNextExercise={nextExercise}
          onPrevExercise={prevExercise}
          onToggleRest={toggleRest}
        />
      ) : null}

      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.14em]">
            {isFinished ? "Finished" : "In progress"}
          </span>
          <h1 className="font-serif mt-1 text-2xl font-medium tracking-tight">
            {s.name ?? "Workout"}
          </h1>
          <SessionTimer
            startedAtMs={new Date(s.started_at).getTime()}
            endedAtMs={s.ended_at ? new Date(s.ended_at).getTime() : null}
            className="text-text-secondary font-serif mt-1 block text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          {!showReadOnly ? (
            <button
              type="button"
              onClick={() => setShortcutsOpen(true)}
              className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold uppercase tracking-[0.08em]"
              title="Keyboard shortcuts (?)"
            >
              ?
            </button>
          ) : null}
          {isFinished ? (
            <>
              <Button
                type="button"
                variant={editMode ? "primary" : "secondary"}
                size="sm"
                onClick={() => setEditMode((v) => !v)}
              >
                {editMode ? "Done editing" : "Edit"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => router.push(`/workouts/${s.id}/summary`)}
              >
                Summary
              </Button>
            </>
          ) : (
            <Button
              type="button"
              onClick={onFinish}
              disabled={finishSession.isPending}
              data-testid="finish-workout"
            >
              {finishSession.isPending ? "Finishing…" : "Finish"}
            </Button>
          )}
        </div>
      </header>

      {!showReadOnly && s.workout_exercises.length > 0 ? (
        <ExerciseRail
          workoutExercises={s.workout_exercises}
          exerciseNames={
            new Map(
              s.workout_exercises.map((we) => [
                we.exercise_id,
                exercisesQuery.data?.get(we.exercise_id)?.name ?? "Exercise",
              ]),
            )
          }
          targetSetsById={targetSetsById}
          activeId={activeWorkoutExerciseId}
          onSelect={selectExercise}
        />
      ) : null}

      {!showReadOnly && plateTargetKg !== null ? (
        <PlateMathStrip targetKg={plateTargetKg} />
      ) : null}

      {showReadOnly ? (
        <ReadOnlySessionView
          workoutExercises={s.workout_exercises}
          exerciseMeta={exercisesQuery.data ?? new Map()}
        />
      ) : s.workout_exercises.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-text-secondary">No exercises yet. Add one to start logging sets.</p>
          </CardContent>
        </Card>
      ) : (
        s.workout_exercises.map((we) => {
          const exMeta = exercisesQuery.data?.get(we.exercise_id);
          return (
            <ExerciseCard
              key={we.id}
              workoutExercise={we}
              exerciseName={exMeta?.name ?? "Exercise"}
              trackingType={exMeta?.tracking_type ?? "weight_reps"}
              onAddSet={async (body) => {
                await addSet.mutateAsync({ workoutExerciseId: we.id, body });
                if (!isFinished) {
                  setRestTotal(DEFAULT_REST_SECONDS);
                  setRestKey(Date.now());
                }
              }}
              onDeleteSet={async (setId) => {
                await deleteSet.mutateAsync(setId);
              }}
              onRemoveExercise={async () => {
                await removeExercise.mutateAsync(we.id);
              }}
            />
          );
        })
      )}

      {!showReadOnly && !isFinished && nextWe ? (
        <NextUpPreview
          name={exerciseNames.get(nextWe.exercise_id) ?? "Exercise"}
          trackingType={exercisesQuery.data?.get(nextWe.exercise_id)?.tracking_type ?? "weight_reps"}
          onSkipAhead={() => selectExercise(nextWe.id)}
        />
      ) : null}

      {!showReadOnly && !isFinished ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() => setPickerOpen(true)}
          data-testid="add-exercise"
        >
          + Add exercise
        </Button>
      ) : null}

      <ExercisePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onPick={(ex) => addExercise.mutate({ exercise_id: ex.id })}
      />

      <KeyboardShortcutsSheet
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />

      {!showReadOnly ? (
        <FloatingRestBar
          activeKey={restKey}
          totalSeconds={restTotal}
          defaultSeconds={DEFAULT_REST_SECONDS}
          onStart={() => {
            setRestTotal(DEFAULT_REST_SECONDS);
            setRestKey(Date.now());
          }}
          onSkip={() => setRestKey(null)}
        />
      ) : null}
    </div>
  );
}
