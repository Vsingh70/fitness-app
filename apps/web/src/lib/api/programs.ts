"use client";

import type { ApiError } from "@/lib/api/client";
import type {
  ActivateRequest,
  ActivateResponse,
  ExerciseDeloadResponse,
  MesocyclePosition,
  Program,
  ProgramCreate,
  ProgramDayCreate,
  ProgramDayExerciseCreate,
  ProgramDayExerciseUpdate,
  ProgramList,
  ProgramTemplateFull,
  ProgramTemplateList,
} from "@/lib/programs/types";

async function call<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    method,
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const err = (payload as { error?: { code?: string; message?: string; details?: unknown } })
      ?.error;
    const apiError: ApiError = {
      status: response.status,
      code: err?.code ?? "internal_error",
      message: err?.message ?? `Request failed with ${response.status}`,
      details: err?.details,
    };
    throw apiError;
  }
  return payload as T;
}

export const listTemplates = () => call<ProgramTemplateList>("GET", "/v1/program-templates");
export const getTemplate = (slug: string) =>
  call<ProgramTemplateFull>("GET", `/v1/program-templates/${slug}`);
export const copyTemplate = (slug: string) =>
  call<Program>("POST", `/v1/program-templates/${slug}/copy`);

export const listMyPrograms = () => call<ProgramList>("GET", "/v1/programs");
export const getProgram = (id: string) => call<Program>("GET", `/v1/programs/${id}`);
export const createProgram = (body: ProgramCreate) => call<Program>("POST", "/v1/programs", body);
export const updateProgram = (id: string, body: Partial<ProgramCreate>) =>
  call<Program>("PATCH", `/v1/programs/${id}`, body);
export const deleteProgram = (id: string) => call<void>("DELETE", `/v1/programs/${id}`);

export const addDay = (programId: string, body: ProgramDayCreate) =>
  call<unknown>("POST", `/v1/programs/${programId}/days`, body);
export const deleteDay = (dayId: string) => call<void>("DELETE", `/v1/program-days/${dayId}`);

export const addExerciseToDay = (dayId: string, body: ProgramDayExerciseCreate) =>
  call<Program>("POST", `/v1/program-days/${dayId}/exercises`, body);
export const updateProgramExercise = (pdeId: string, body: ProgramDayExerciseUpdate) =>
  call<Program>("PATCH", `/v1/program-day-exercises/${pdeId}`, body);
export const deleteProgramExercise = (pdeId: string) =>
  call<void>("DELETE", `/v1/program-day-exercises/${pdeId}`);

export const activateProgram = (id: string, body: ActivateRequest) =>
  call<ActivateResponse>("POST", `/v1/programs/${id}/activate`, body);
export const deactivateProgram = (id: string) =>
  call<Program>("POST", `/v1/programs/${id}/deactivate`);

export const getMesocycle = (id: string) =>
  call<MesocyclePosition>("GET", `/v1/programs/${id}/mesocycle`);

/** Reactive per-lift deload for a continuous program (no request body). */
export const deloadExercise = (programId: string, exerciseId: string) =>
  call<ExerciseDeloadResponse>(
    "POST",
    `/v1/programs/${programId}/exercises/${exerciseId}/deload`,
  );
