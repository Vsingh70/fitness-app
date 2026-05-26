"use client";

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/workouts";
import { enqueue } from "@/lib/offline/queue";
import { newIdempotencyKey } from "@/lib/api/workouts";
import type {
  SetCreate,
  SetUpdate,
  WorkoutExercise,
  WorkoutSession,
  WorkoutSet,
} from "@/lib/workouts/types";

const SESSION_KEY = (id: string) => ["workout-session", id] as const;
const SESSIONS_LIST_KEY = (limit: number) => ["workout-sessions", { limit }] as const;

export function useSession(id: string | null | undefined) {
  return useQuery({
    queryKey: SESSION_KEY(id ?? "none"),
    queryFn: () => api.getSession(id as string),
    enabled: !!id,
    staleTime: 10_000,
  });
}

export function useRecentSessions(limit = 5) {
  return useQuery({
    queryKey: SESSIONS_LIST_KEY(limit),
    queryFn: () => api.listSessions({ limit }),
    staleTime: 30_000,
  });
}

export function useCreateEmptySession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name?: string } = {}) => api.createSession(input),
    onSuccess: (session) => {
      qc.setQueryData(SESSION_KEY(session.id), session);
      qc.invalidateQueries({ queryKey: ["workout-sessions"] });
    },
  });
}

export function useAddExercise(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { exercise_id: string; notes?: string | null }) =>
      api.addExercise(sessionId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SESSION_KEY(sessionId) });
    },
  });
}

export function useReorderExercise(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { workoutExerciseId: string; position: number }) =>
      api.reorderExercise(input.workoutExerciseId, input.position),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SESSION_KEY(sessionId) });
    },
  });
}

export function useRemoveExercise(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (workoutExerciseId: string) => api.removeExercise(workoutExerciseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SESSION_KEY(sessionId) });
    },
  });
}

interface AddSetInput {
  workoutExerciseId: string;
  body: SetCreate;
}

/** Optimistic add: prepend a temp set immediately, replace with server result. */
export function useAddSet(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ workoutExerciseId, body }: AddSetInput) => {
      const key = newIdempotencyKey();
      try {
        return await api.addSet(workoutExerciseId, body, key);
      } catch (err) {
        // Network/offline: enqueue and let the UI keep its optimistic row.
        if (typeof navigator !== "undefined" && !navigator.onLine) {
          await enqueue({
            kind: "add_set",
            workoutExerciseId,
            body,
            idempotencyKey: key,
            queuedAt: Date.now(),
          });
          return makeOptimisticSet(body);
        }
        throw err;
      }
    },
    onMutate: async ({ workoutExerciseId, body }) => {
      await qc.cancelQueries({ queryKey: SESSION_KEY(sessionId) });
      const previous = qc.getQueryData<WorkoutSession>(SESSION_KEY(sessionId));
      const optimistic = makeOptimisticSet(body);
      mutateSession(qc, sessionId, (s) => addSetTo(s, workoutExerciseId, optimistic));
      return { previous, optimisticId: optimistic.id };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(SESSION_KEY(sessionId), ctx.previous);
    },
    onSuccess: (real, vars, ctx) => {
      mutateSession(qc, sessionId, (s) =>
        replaceSet(s, vars.workoutExerciseId, ctx?.optimisticId ?? null, real),
      );
    },
  });
}

export function useUpdateSet(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ setId, body }: { setId: string; body: SetUpdate }) => api.updateSet(setId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SESSION_KEY(sessionId) });
    },
  });
}

export function useDeleteSet(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (setId: string) => api.deleteSet(setId),
    onMutate: async (setId) => {
      await qc.cancelQueries({ queryKey: SESSION_KEY(sessionId) });
      const previous = qc.getQueryData<WorkoutSession>(SESSION_KEY(sessionId));
      mutateSession(qc, sessionId, (s) => removeSet(s, setId));
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(SESSION_KEY(sessionId), ctx.previous);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SESSION_KEY(sessionId) });
    },
  });
}

export function useFinishSession(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.finishSession(sessionId),
    onSuccess: (session) => {
      qc.setQueryData(SESSION_KEY(sessionId), session);
      qc.invalidateQueries({ queryKey: ["workout-sessions"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Local helpers (optimistic mutation plumbing).
// ---------------------------------------------------------------------------

function makeOptimisticSet(body: SetCreate): WorkoutSet {
  const now = Date.now();
  const tempId =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? `tmp-${crypto.randomUUID()}`
      : `tmp-${now}-${Math.random()}`;
  return {
    id: tempId,
    set_index: -1,
    set_type: body.set_type ?? "working",
    weight_kg: (body.weight_kg as never) ?? null,
    reps: body.reps ?? null,
    duration_seconds: body.duration_seconds ?? null,
    distance_meters: (body.distance_meters as never) ?? null,
    rpe: (body.rpe as never) ?? null,
    rir: body.rir ?? null,
    is_pr: false,
    notes: body.notes ?? null,
    // Marker fields aren't on the schema; we tag pending via a sentinel id prefix.
  } as WorkoutSet & { __pending?: boolean };
}

function mutateSession(
  qc: QueryClient,
  sessionId: string,
  fn: (s: WorkoutSession) => WorkoutSession,
): void {
  qc.setQueryData<WorkoutSession>(SESSION_KEY(sessionId), (prev) => (prev ? fn(prev) : prev));
}

function addSetTo(
  session: WorkoutSession,
  workoutExerciseId: string,
  newSet: WorkoutSet,
): WorkoutSession {
  return {
    ...session,
    workout_exercises: session.workout_exercises.map((we: WorkoutExercise) =>
      we.id === workoutExerciseId ? { ...we, sets: [...we.sets, newSet] } : we,
    ),
  };
}

function replaceSet(
  session: WorkoutSession,
  workoutExerciseId: string,
  optimisticId: string | null,
  real: WorkoutSet,
): WorkoutSession {
  return {
    ...session,
    workout_exercises: session.workout_exercises.map((we: WorkoutExercise) =>
      we.id === workoutExerciseId
        ? {
            ...we,
            sets: we.sets.map((s) => (s.id === optimisticId ? real : s)),
          }
        : we,
    ),
  };
}

function removeSet(session: WorkoutSession, setId: string): WorkoutSession {
  return {
    ...session,
    workout_exercises: session.workout_exercises.map((we: WorkoutExercise) => ({
      ...we,
      sets: we.sets.filter((s) => s.id !== setId),
    })),
  };
}
