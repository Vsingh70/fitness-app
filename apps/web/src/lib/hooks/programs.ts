"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/programs";
import type {
  ActivateRequest,
  ProgramCreate,
  ProgramDayCreate,
  ProgramDayExerciseCreate,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";

const TEMPLATES_KEY = ["program-templates"] as const;
const TEMPLATE_KEY = (slug: string) => ["program-template", slug] as const;
const MY_PROGRAMS_KEY = ["programs", "mine"] as const;
const PROGRAM_KEY = (id: string) => ["program", id] as const;

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
    queryFn: api.listMyPrograms,
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

export function useAddDay(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProgramDayCreate) => api.addDay(programId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
  });
}

export function useDeleteDay(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dayId: string) => api.deleteDay(dayId),
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
  });
}

export function useDeleteProgramExercise(programId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pdeId: string) => api.deleteProgramExercise(pdeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROGRAM_KEY(programId) }),
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
