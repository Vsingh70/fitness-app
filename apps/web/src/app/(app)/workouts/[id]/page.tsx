"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ExerciseCard } from "@/components/workouts/exercise-card";
import { ExercisePicker } from "@/components/workouts/exercise-picker";
import { KeyboardShortcuts } from "@/components/workouts/keyboard-shortcuts";
import { RestTimer } from "@/components/workouts/rest-timer";
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
import type { Exercise } from "@/lib/workouts/types";

const DEFAULT_REST_SECONDS = 90;

export default function WorkoutInProgressPage() {
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
  const [restKey, setRestKey] = useState<number | null>(null);

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

  if (session.isLoading) return <p className="text-text-secondary">Loading session...</p>;
  if (session.isError) return <p className="text-destructive">Could not load session.</p>;
  if (!session.data) return null;

  const s = session.data;
  const isFinished = !!s.ended_at;

  const onFinish = () => {
    finishSession.mutate(undefined, {
      onSuccess: () => {
        clearActive();
        router.push(`/workouts/${s.id}/summary`);
      },
    });
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <KeyboardShortcuts onAddExercise={() => setPickerOpen(true)} />
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{s.name ?? "Workout"}</h1>
          <SessionTimer
            startedAtMs={new Date(s.started_at).getTime()}
            endedAtMs={s.ended_at ? new Date(s.ended_at).getTime() : null}
            className="text-text-secondary text-sm"
          />
        </div>
        {!isFinished ? (
          <Button
            type="button"
            onClick={onFinish}
            disabled={finishSession.isPending}
            data-testid="finish-workout"
          >
            {finishSession.isPending ? "Finishing..." : "Finish"}
          </Button>
        ) : (
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push(`/workouts/${s.id}/summary`)}
          >
            View summary
          </Button>
        )}
      </header>

      {restKey !== null ? (
        <Card>
          <CardContent className="flex items-center justify-between">
            <RestTimer
              key={restKey}
              seconds={DEFAULT_REST_SECONDS}
              onComplete={() => setRestKey(null)}
            />
            <Button type="button" variant="ghost" size="sm" onClick={() => setRestKey(null)}>
              Skip rest
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {s.workout_exercises.length === 0 ? (
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
                if (!isFinished) setRestKey(Date.now());
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

      {!isFinished ? (
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
    </div>
  );
}
