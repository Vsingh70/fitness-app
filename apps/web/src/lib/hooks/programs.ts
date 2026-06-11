"use client";

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/programs";
import type {
  ActivateRequest,
  Program,
  ProgramCreate,
  ProgramDayCreate,
  ProgramDayExerciseCreate,
  ProgramDayExerciseUpdate,
  ProgramList,
} from "@/lib/programs/types";

const TEMPLATES_KEY = ["program-templates"] as const;
const TEMPLATE_KEY = (slug: string) => ["program-template", slug] as const;
const MY_PROGRAMS_KEY = ["programs", "mine"] as const;
const PROGRAM_KEY = (id: string) => ["program", id] as const;
const MESOCYCLE_KEY = (id: string) => ["program", id, "mesocycle"] as const;

/** Patch the cached program in place; fall back to a refetch when it isn't cached. */
function patchProgram(qc: QueryClient, programId: string, update: (prev: Program) => Program) {
  const prev = qc.getQueryData<Program>(PROGRAM_KEY(programId));
  if (prev) qc.setQueryData(PROGRAM_KEY(programId), update(prev));
  else qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) });
}

/** Sync a single program's fields into the cached "my programs" list (no refetch). */
function patchProgramListItem(qc: QueryClient, program: Program) {
  qc.setQueryData<ProgramList>(MY_PROGRAMS_KEY, (prev) =>
    prev
      ? {
          ...prev,
          items: prev.items.map((item) =>
            item.id === program.id
              ? {
                  ...item,
                  name: program.name,
                  goal: program.goal,
                  weeks: program.weeks,
                  days_per_week: program.days_per_week,
                  is_active: program.is_active,
                  activated_at: program.activated_at,
                  source: program.source,
                }
              : item,
          ),
        }
      : prev,
  );
}

export function useTemplates() {
  return useQuery({
    queryKey: TEMPLATES_KEY,
    queryFn: api.listTemplates,
    staleTime: 5 * 60_000,
  });
}

export function useTemplate(slug: string | null | undefined) {
  return useQuery({
    queryKey: TEMPLATE_KEY(slug ?? "none"),
    queryFn: () => api.getTemplate(slug as string),
    enabled: !!slug,
    staleTime: 5 * 60_000,
  });
}

export function useMyPrograms() {
  return useQuery({
    queryKey: MY_PROGRAMS_KEY,
    // Settings and the plan wizard need the complete list, so follow the
    // cursor to exhaustion instead of paging in the UI.
    queryFn: async (): Promise<ProgramList> => {
      const items: ProgramList["items"] = [];
      let cursor: string | undefined;
      do {
        const page = await api.listMyPrograms({ limit: 100, cursor });
        items.push(...page.items);
        cursor = page.next_cursor ?? undefined;
      } while (cursor);
      return { items, next_cursor: null };
    },
    staleTime: 30_000,
  });
}

export function useProgram(id: string | null | undefined) {
  return useQuery({
    queryKey: PROGRAM_KEY(id ?? "none"),
    queryFn: () => api.getProgram(id as string),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useMesocycle(id: string | null | undefined) {
  return useQuery({
    queryKey: MESOCYCLE_KEY(id ?? "none"),
    queryFn: () => api.getMesocycle(id as string),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useCopyTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => api.copyTemplate(slug),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}

export function useCreateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProgramCreate) => api.createProgram(body),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}

export function useUpdateProgram(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<ProgramCreate>) => api.updateProgram(programId, body),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      patchProgramListItem(qc, program);
      qc.invalidateQueries({ queryKey: MESOCYCLE_KEY(program.id) });
    },
  });
}

export function useAddDay(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProgramDayCreate) => api.addDay(programId, body),
    onSuccess: (day) =>
      patchProgram(qc, programId, (prev) => ({
        ...prev,
        days: [...prev.days, day].sort((a, b) => a.day_index - b.day_index),
      })),
  });
}

export function useDeleteDay(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dayId: string) => api.deleteDay(dayId),
    // 204 response and the server reindexes day_index of the remaining days,
    // so the cached shape can't be reconstructed locally — refetch.
    onSuccess: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
  });
}

export function useAddExerciseToDay(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { dayId: string; body: ProgramDayExerciseCreate }) =>
      api.addExerciseToDay(args.dayId, args.body),
    onSuccess: (program) => qc.setQueryData(PROGRAM_KEY(programId), program),
  });
}

export function useUpdateProgramExercise(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { pdeId: string; body: ProgramDayExerciseUpdate }) =>
      api.updateProgramExercise(args.pdeId, args.body),
    onSuccess: (program) => qc.setQueryData(PROGRAM_KEY(programId), program),
    // A rejected PATCH (e.g. 422) would otherwise leave the editor's drafts
    // showing the unsaved value; a refetch re-syncs them via their value props.
    onError: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
  });
}

export function useDeleteProgramExercise(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pdeId: string) => api.deleteProgramExercise(pdeId),
    onSuccess: (_res, pdeId) =>
      patchProgram(qc, programId, (prev) => ({
        ...prev,
        days: prev.days.map((d) => ({
          ...d,
          exercises: d.exercises.filter((e) => e.id !== pdeId),
        })),
      })),
  });
}

export function useDeleteProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) => api.deleteProgram(programId),
    onSuccess: (_res, programId) => {
      // Drop the deleted program from the cached list without a refetch, and
      // clear its single-program cache entry.
      qc.setQueryData<ProgramList>(MY_PROGRAMS_KEY, (prev) =>
        prev ? { ...prev, items: prev.items.filter((item) => item.id !== programId) } : prev,
      );
      qc.removeQueries({ queryKey: PROGRAM_KEY(programId) });
    },
  });
}

export function useActivateProgram(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ActivateRequest) => api.activateProgram(programId, body),
    onSuccess: ({ program }) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}

export function useDeactivateProgram(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.deactivateProgram(programId),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}

/**
 * Apply a reactive per-lift deload (continuous mode). Driven by a stagnation
 * insight that carries `program_id` + `exercise_id`. On success we refetch
 * insights so the resolved suggestion clears, plus the program itself.
 */
export function useDeloadExercise() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { programId: string; exerciseId: string }) =>
      api.deloadExercise(args.programId, args.exerciseId),
    onSuccess: (_res, { programId }) => {
      qc.invalidateQueries({ queryKey: ["insights"] });
      qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) });
    },
  });
}

/** Deactivate a program whose id is supplied at call time (e.g. settings). */
export function useDeactivateAnyProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) => api.deactivateProgram(programId),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}
