"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as programsApi from "@/lib/api/programs";
import * as schedulingApi from "@/lib/api/scheduling";
import type {
  Program,
  ProgramDay,
  ProgramDayExercise,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";
import type { WorkoutSession } from "@/lib/workouts/types";

/**
 * Resolve the active program slot behind an in-progress session (05 §3). A
 * session links to a `scheduled_workout`; that scheduled row carries the
 * `program_id` and `program_day_id` (the rotation slot). With both we can fetch
 * the program and reach the slot's exercises so "Change in program" /
 * "Remove from program" writes the same slot the builder edits.
 *
 * Freestyle sessions have no `scheduled_workout_id`; this returns `null`
 * everywhere so the UI hides the program-edit actions (there is no slot).
 */
export interface SessionProgramContext {
  /** True once enough has loaded to know whether a program slot exists. */
  resolved: boolean;
  /** The owning program, when the session is program-linked. */
  program: Program | null;
  /** The rotation slot this session was started from. */
  slot: ProgramDay | null;
  /** Map an exercise id to its slot-exercise row (for update/delete targeting). */
  slotExerciseFor: (exerciseId: string) => ProgramDayExercise | null;
}

const SCHEDULED_RANGE_KEY = ["scheduled-workouts", "program-context"] as const;

export function useSessionProgramContext(
  session: WorkoutSession | undefined,
): SessionProgramContext {
  const scheduledId = session?.scheduled_workout_id ?? null;

  // The scheduled list is the only place that maps a scheduled workout to its
  // program + slot ids. We fetch a wide window once and read the row by id; the
  // list is cached and shared with the calendar.
  const scheduled = useQuery({
    queryKey: SCHEDULED_RANGE_KEY,
    queryFn: () => schedulingApi.listScheduled(programContextRange()),
    enabled: !!scheduledId,
    staleTime: 60_000,
  });

  const row = useMemo(
    () =>
      scheduledId ? (scheduled.data?.items.find((it) => it.id === scheduledId) ?? null) : null,
    [scheduled.data, scheduledId],
  );
  const programId = row?.program_id ?? null;
  const slotId = row?.program_day_id ?? null;

  const program = useQuery({
    queryKey: ["program", programId ?? "none"],
    queryFn: () => programsApi.getProgram(programId as string),
    enabled: !!programId,
    staleTime: 30_000,
  });

  const slot = useMemo(
    () => (slotId ? (program.data?.days.find((d) => d.id === slotId) ?? null) : null),
    [program.data, slotId],
  );

  const slotExerciseFor = useMemo(() => {
    const byExercise = new Map<string, ProgramDayExercise>();
    if (slot) for (const ex of slot.exercises) byExercise.set(ex.exercise_id, ex);
    return (exerciseId: string) => byExercise.get(exerciseId) ?? null;
  }, [slot]);

  // "Resolved" means: not a program session (no scheduledId), or the scheduled
  // row + program have both settled. Until then the UI shows nothing rather than
  // flashing a wrong affordance.
  const resolved = !scheduledId ? true : scheduled.isFetched && (!programId || program.isFetched);

  return {
    resolved,
    program: program.data ?? null,
    slot,
    slotExerciseFor,
  };
}

/** A ±60d window: wide enough to contain the slot a live session started from. */
function programContextRange(): { from: string; to: string } {
  const now = Date.now();
  const day = 86_400_000;
  const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
  return { from: iso(now - 60 * day), to: iso(now + 60 * day) };
}

/**
 * Edit a slot exercise's targets in the active program (05 §3, "Change in
 * program"). Writes the same slot endpoint the builder uses; applies now and
 * forward. The in-progress session's logged sets are untouched — this never
 * mutates the session cache.
 */
export function useChangeProgramTargets(programId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { pdeId: string; body: ProgramDayExerciseUpdate }) =>
      programsApi.updateProgramExercise(args.pdeId, args.body),
    onSuccess: (program) => {
      if (programId) qc.setQueryData(["program", programId], program);
    },
  });
}

/**
 * Swap a slot exercise in the active program (05 §3): drop the old slot exercise
 * and add the substitute to the same slot, carrying the original's targets so
 * the swap keeps sets/reps/intensity. Applies now and forward.
 */
export function useSwapInProgram(programId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      slotId: string;
      pde: ProgramDayExercise;
      substituteExerciseId: string;
    }) => {
      await programsApi.deleteProgramExercise(args.pde.id);
      return programsApi.addExerciseToSlot(args.slotId, {
        exercise_id: args.substituteExerciseId,
        block_kind: args.pde.block_kind,
        progression_strategy: args.pde.progression_strategy,
        rep_mode: args.pde.rep_mode,
        target_sets: args.pde.target_sets,
        target_reps_low: args.pde.target_reps_low,
        target_reps_high: args.pde.target_reps_high,
        target_rir_low: args.pde.target_rir_low,
        target_rir_high: args.pde.target_rir_high,
        target_rpe_low: args.pde.target_rpe_low,
        target_rpe_high: args.pde.target_rpe_high,
        rest_seconds: args.pde.rest_seconds,
      });
    },
    onSuccess: (program) => {
      if (programId) qc.setQueryData(["program", programId], program);
    },
    onError: () => {
      // A half-applied swap (delete landed, add failed) must re-sync from server.
      if (programId) qc.invalidateQueries({ queryKey: ["program", programId] });
    },
  });
}

/** Remove a slot exercise from the active program (05 §3, "Remove from program"). */
export function useRemoveFromProgram(programId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pdeId: string) => programsApi.deleteProgramExercise(pdeId),
    onSuccess: () => {
      if (programId) qc.invalidateQueries({ queryKey: ["program", programId] });
    },
  });
}
