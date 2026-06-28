import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ProgramBuilder } from "@/components/programs/program-builder";
import * as programsApi from "@/lib/api/programs";
import type { Program, ProgramDay } from "@/lib/programs/types";

// A single mutable program the mocked API reads/writes, so slot edits round-trip
// through the real useProgram/useToggleRest/useRenameSlot/useDeleteSlot hooks and
// the builder's local order mirror — exercising the reactivity fix end to end.
const state = vi.hoisted(() => ({ program: null as unknown as Program }));

vi.mock("@/lib/api/programs", () => ({
  getProgram: vi.fn(async () => state.program),
  updateSlot: vi.fn(
    async (slotId: string, body: { is_rest_day?: boolean | null; name?: string | null }) => {
      state.program = {
        ...state.program,
        days: state.program.days.map((d) =>
          d.id === slotId
            ? {
                ...d,
                ...(body.is_rest_day != null ? { is_rest_day: body.is_rest_day } : {}),
                ...(body.name != null ? { name: body.name } : {}),
              }
            : d,
        ),
      };
      return state.program;
    },
  ),
  deleteSlot: vi.fn(async (slotId: string) => {
    state.program = {
      ...state.program,
      days: state.program.days.filter((d) => d.id !== slotId),
    };
    return undefined;
  }),
}));

// The builder pulls exercise metadata and lazy-loads the exercise picker; neither
// is relevant to slot management, so stub them out for an isolated render.
vi.mock("@/lib/hooks/exercises", () => ({ useExerciseMeta: () => ({ data: new Map() }) }));
vi.mock("next/dynamic", () => ({ default: () => () => null }));

function slot(overrides: Partial<ProgramDay> = {}): ProgramDay {
  return {
    id: "s1",
    name: "Slot 1",
    is_rest_day: false,
    slot_index: 0,
    exercises: [],
    ...overrides,
  };
}

function makeProgram(overrides: Partial<Program> = {}): Program {
  return {
    id: "p1",
    name: "PPL",
    description: null,
    goal: "hypertrophy",
    periodization_mode: "block",
    intensity_mode: "rpe",
    is_active: false,
    activated_at: null,
    auto_deload: false,
    auto_deload_on_stall: false,
    mesocycle_length_microcycles: 4,
    microcycle_length: 1,
    source: "manual",
    template_id: null,
    created_at: "2026-01-01T00:00:00Z",
    days: [slot()],
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ProgramBuilder slot management", () => {
  beforeEach(() => {
    state.program = makeProgram();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("reflects a rest-day toggle immediately, with no further edit", async () => {
    const user = userEvent.setup();
    render(<ProgramBuilder programId="p1" />, { wrapper });

    const rest = await screen.findByLabelText("Rest day");
    expect(rest).not.toBeChecked();
    expect(screen.queryByText("Rest day, no exercises.")).toBeNull();

    await user.click(rest);

    // Regression: previously the local order mirror re-synced only when the slot
    // id-set changed, so the panel stayed stale until an add/delete.
    await waitFor(() => expect(screen.getByText("Rest day, no exercises.")).toBeInTheDocument());
    expect(screen.getByLabelText("Rest day")).toBeChecked();
  });

  it("renames a slot inline on blur", async () => {
    const user = userEvent.setup();
    render(<ProgramBuilder programId="p1" />, { wrapper });

    const field = await screen.findByLabelText("Slot name");
    await user.clear(field);
    await user.type(field, "Upper Body");
    await user.tab();

    await waitFor(() =>
      expect(programsApi.updateSlot).toHaveBeenCalledWith("s1", { name: "Upper Body" }),
    );
    // The rail label reflects the persisted name.
    await waitFor(() => expect(screen.getByText("Upper Body")).toBeInTheDocument());
  });

  it("reverts the slot name on Escape without persisting", async () => {
    const user = userEvent.setup();
    render(<ProgramBuilder programId="p1" />, { wrapper });

    const field = await screen.findByLabelText("Slot name");
    await user.clear(field);
    await user.type(field, "Discarded");
    await user.keyboard("{Escape}");

    expect(programsApi.updateSlot).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByLabelText("Slot name")).toHaveValue("Slot 1"));
  });

  it("deletes a slot from the rail", async () => {
    state.program = makeProgram({
      days: [slot(), slot({ id: "s2", name: "Slot 2", slot_index: 1 })],
      microcycle_length: 2,
    });
    const user = userEvent.setup();
    render(<ProgramBuilder programId="p1" />, { wrapper });

    await screen.findByText("Slot 2");
    await user.click(screen.getByRole("button", { name: "Delete Slot 2" }));

    await waitFor(() => expect(programsApi.deleteSlot).toHaveBeenCalledWith("s2"));
    await waitFor(() => expect(screen.queryByText("Slot 2")).toBeNull());
  });
});
