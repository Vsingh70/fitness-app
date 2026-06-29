"use client";

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/programs";
import type {
  AdvanceRequest,
  Program,
  ProgramCreate,
  ProgramDayCreate,
  ProgramDayExerciseCreate,
  ProgramDayExerciseUpdate,
  ProgramList,
  ProgramTemplateList,
  ProgramUpdate,
  SaveAsTemplateRequest,
} from "@/lib/programs/types";

const TEMPLATES_KEY = ["program-templates"] as const;
const TEMPLATE_KEY = (slug: string) => ["program-template", slug] as const;
const MY_PROGRAMS_KEY = ["programs", "mine"] as const;
const PROGRAM_KEY = (id: string) => ["program", id] as const;
const POSITION_KEY = (id: string) => ["program", id, "position"] as const;

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
                  microcycle_length: program.microcycle_length,
                  mesocycle_length_microcycles: program.mesocycle_length_microcycles,
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

export function usePosition(id: string | null | undefined) {
  return useQuery({
    queryKey: POSITION_KEY(id ?? "none"),
    queryFn: () => api.getPosition(id as string),
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

/**
 * Delete a user-owned template (the user's own saved templates only — curated
 * and partner-shared templates have no delete affordance). Drops the row from
 * the cached templates list without a refetch.
 */
export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => api.deleteTemplate(slug),
    onSuccess: (_res, slug) => {
      qc.setQueryData<ProgramTemplateList>(TEMPLATES_KEY, (prev) =>
        prev ? { ...prev, items: prev.items.filter((t) => t.slug !== slug) } : prev,
      );
      qc.removeQueries({ queryKey: TEMPLATE_KEY(slug) });
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
    mutationFn: (body: ProgramUpdate) => api.updateProgram(programId, body),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      patchProgramListItem(qc, program);
      qc.invalidateQueries({ queryKey: POSITION_KEY(program.id) });
    },
  });
}

export function useAddSlot(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProgramDayCreate) => api.addSlot(programId, body),
    onSuccess: (slot) =>
      patchProgram(qc, programId, (prev) => ({
        ...prev,
        days: [...prev.days, slot].sort((a, b) => a.slot_index - b.slot_index),
        microcycle_length: prev.days.length + 1,
      })),
  });
}

export function useDeleteSlot(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slotId: string) => api.deleteSlot(slotId),
    // 204 response and the server reindexes slot_index of the remaining slots,
    // so the cached shape can't be reconstructed locally — refetch.
    onSuccess: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
  });
}

/** Persist a new slot ordering (drag-reorder); server returns the full program. */
export function useReorderSlots(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slotIds: string[]) => api.reorderSlots(programId, { slot_ids: slotIds }),
    onSuccess: (program) => qc.setQueryData(PROGRAM_KEY(programId), program),
    // A rejected reorder would otherwise leave the rail showing the optimistic
    // order; a refetch re-syncs the canonical slot_index ordering.
    onError: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
  });
}

/** Toggle a slot's rest flag via the slot PATCH; server returns the full program. */
export function useToggleRest(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { slotId: string; isRestDay: boolean }) =>
      api.updateSlot(args.slotId, { is_rest_day: args.isRestDay }),
    onSuccess: (program) => qc.setQueryData(PROGRAM_KEY(programId), program),
  });
}

/** Rename a slot via the slot PATCH; server returns the full program. */
export function useRenameSlot(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { slotId: string; name: string }) =>
      api.updateSlot(args.slotId, { name: args.name }),
    onSuccess: (program) => qc.setQueryData(PROGRAM_KEY(programId), program),
  });
}

export function useAddExerciseToSlot(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { slotId: string; body: ProgramDayExerciseCreate }) =>
      api.addExerciseToSlot(args.slotId, args.body),
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

/**
 * Persist a drag-reordering of a slot's exercises. There's no dedicated endpoint
 * (unlike slots), but `position` is PATCH-settable and unconstrained, so we
 * renumber each exercise 0..n. The cache is updated optimistically for an instant
 * drop; a failed PATCH refetches to re-sync the canonical order.
 */
export function useReorderExercises(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    // Serialise concurrent reorders (a rapid re-drag) so position writes can't race.
    scope: { id: `reorder-exercises-${programId}` },
    // Write positions sequentially: a partial failure stops cleanly, and the writes
    // never interleave with each other within a batch.
    mutationFn: async (args: { slotId: string; orderedIds: string[] }) => {
      for (const [i, id] of args.orderedIds.entries()) {
        await api.updateProgramExercise(id, { position: i });
      }
    },
    onMutate: (args) =>
      patchProgram(qc, programId, (prev) => ({
        ...prev,
        days: prev.days.map((d) => {
          if (d.id !== args.slotId) return d;
          const byId = new Map(d.exercises.map((e) => [e.id, e]));
          const exercises = args.orderedIds
            .map((id, i) => {
              const ex = byId.get(id);
              return ex ? { ...ex, position: i } : undefined;
            })
            .filter((e): e is (typeof d.exercises)[number] => e !== undefined);
          return { ...d, exercises };
        }),
      })),
    onError: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
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
    mutationFn: () => api.activateProgram(programId),
    onSuccess: (program) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
      qc.invalidateQueries({ queryKey: POSITION_KEY(program.id) });
    },
  });
}

/** Duplicate a program into a new editable copy (inactive); lands on the copy. */
export function useDuplicateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) => api.duplicateProgram(programId),
    onSuccess: ({ program }) => {
      qc.setQueryData(PROGRAM_KEY(program.id), program);
      qc.invalidateQueries({ queryKey: MY_PROGRAMS_KEY });
    },
  });
}

/** Save a program as a reusable template (name + visibility). */
export function useSaveAsTemplate(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SaveAsTemplateRequest) => api.saveAsTemplate(programId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: TEMPLATES_KEY }),
  });
}

/** Advance an active program's rotation position (optionally as a skip). */
export function useAdvancePosition(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body?: AdvanceRequest) => api.advancePosition(programId, body),
    onSuccess: (position) => qc.setQueryData(POSITION_KEY(programId), position),
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
