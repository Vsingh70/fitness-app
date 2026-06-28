"use client";

import type { ApiError } from "@/lib/api/client";
import type {
  AdvanceRequest,
  DuplicateProgramResponse,
  ExerciseDeloadResponse,
  Program,
  ProgramCreate,
  ProgramDay,
  ProgramDayCreate,
  ProgramDayExerciseCreate,
  ProgramDayExerciseUpdate,
  ProgramDayUpdate,
  ProgramList,
  ProgramPosition,
  ProgramTemplateFull,
  ProgramTemplateList,
  ProgramUpdate,
  SaveAsTemplateRequest,
  SaveAsTemplateResponse,
  SlotReorderRequest,
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
export const deleteTemplate = (slug: string) =>
  call<void>("DELETE", `/v1/program-templates/${slug}`);

export const listMyPrograms = (params: { limit?: number; cursor?: string } = {}) => {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", params.cursor);
  const qs = q.toString();
  return call<ProgramList>("GET", `/v1/programs${qs ? `?${qs}` : ""}`);
};
export const getProgram = (id: string) => call<Program>("GET", `/v1/programs/${id}`);
export const createProgram = (body: ProgramCreate) => call<Program>("POST", "/v1/programs", body);
export const updateProgram = (id: string, body: ProgramUpdate) =>
  call<Program>("PATCH", `/v1/programs/${id}`, body);
export const deleteProgram = (id: string) => call<void>("DELETE", `/v1/programs/${id}`);

// Slots (formerly "days"): a slot is a position in the microcycle rotation; the
// microcycle length is simply the number of slots.
export const addSlot = (programId: string, body: ProgramDayCreate) =>
  call<ProgramDay>("POST", `/v1/programs/${programId}/slots`, body);
export const deleteSlot = (slotId: string) => call<void>("DELETE", `/v1/program-slots/${slotId}`);
export const updateSlot = (slotId: string, body: ProgramDayUpdate) =>
  call<Program>("PATCH", `/v1/program-slots/${slotId}`, body);
export const reorderSlots = (programId: string, body: SlotReorderRequest) =>
  call<Program>("POST", `/v1/programs/${programId}/slots/reorder`, body);

export const addExerciseToSlot = (slotId: string, body: ProgramDayExerciseCreate) =>
  call<Program>("POST", `/v1/program-slots/${slotId}/exercises`, body);
export const updateProgramExercise = (pdeId: string, body: ProgramDayExerciseUpdate) =>
  call<Program>("PATCH", `/v1/program-day-exercises/${pdeId}`, body);
export const deleteProgramExercise = (pdeId: string) =>
  call<void>("DELETE", `/v1/program-day-exercises/${pdeId}`);

export const activateProgram = (id: string) => call<Program>("POST", `/v1/programs/${id}/activate`);
export const deactivateProgram = (id: string) =>
  call<Program>("POST", `/v1/programs/${id}/deactivate`);

export const getPosition = (id: string) =>
  call<ProgramPosition>("GET", `/v1/programs/${id}/position`);
export const advancePosition = (id: string, body?: AdvanceRequest) =>
  call<ProgramPosition>("POST", `/v1/programs/${id}/advance`, body);

export const duplicateProgram = (id: string) =>
  call<DuplicateProgramResponse>("POST", `/v1/programs/${id}/duplicate`);
export const saveAsTemplate = (id: string, body: SaveAsTemplateRequest) =>
  call<SaveAsTemplateResponse>("POST", `/v1/programs/${id}/save-as-template`, body);

/** Reactive per-lift deload for a continuous program (no request body). */
export const deloadExercise = (programId: string, exerciseId: string) =>
  call<ExerciseDeloadResponse>("POST", `/v1/programs/${programId}/exercises/${exerciseId}/deload`);
