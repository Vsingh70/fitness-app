import { describe, expect, it } from "vitest";

import { groupByCycle, projectRotation } from "@/lib/programs/rotation";
import type { Program, ProgramDay, ProgramPosition } from "@/lib/programs/types";

function slot(index: number, name: string, isRest = false): ProgramDay {
  return {
    id: `slot-${index}`,
    name,
    slot_index: index,
    is_rest_day: isRest,
    exercises: [],
  };
}

/** Push / Pull / Legs / Rest, matching the model spec's worked example shape. */
function makeProgram(overrides: Partial<Program> = {}): Program {
  return {
    id: "prog-1",
    name: "PPL",
    description: null,
    goal: "hypertrophy",
    source: "manual",
    template_id: null,
    is_active: true,
    activated_at: "2026-06-01T00:00:00Z",
    created_at: "2026-06-01T00:00:00Z",
    microcycle_length: 4,
    mesocycle_length_microcycles: 4,
    auto_deload: false,
    auto_deload_on_stall: false,
    periodization_mode: "none",
    intensity_mode: "off",
    days: [slot(0, "Push"), slot(1, "Pull"), slot(2, "Legs"), slot(3, "Rest", true)],
    ...overrides,
  } as Program;
}

function makePosition(overrides: Partial<ProgramPosition> = {}): ProgramPosition {
  return {
    current_slot_index: 0,
    current_repetition: 1,
    current_microcycle_number: 1,
    in_deload: false,
    is_rest_day: false,
    mesocycle_length_microcycles: 4,
    next_training_slot: null,
    today_slot: null,
    ...overrides,
  };
}

describe("projectRotation", () => {
  it("projects slots forward in order from the current position", () => {
    const out = projectRotation(makeProgram(), makePosition(), 5);
    expect(out.map((p) => p.slot.name)).toEqual(["Push", "Pull", "Legs", "Rest", "Push"]);
    expect(out[0]!.isCurrent).toBe(true);
    expect(out[1]!.isCurrent).toBe(false);
  });

  it("starts from a mid-microcycle slot index", () => {
    const out = projectRotation(makeProgram(), makePosition({ current_slot_index: 2 }), 3);
    expect(out.map((p) => p.slot.name)).toEqual(["Legs", "Rest", "Push"]);
  });

  it("marks rest slots", () => {
    const out = projectRotation(makeProgram(), makePosition(), 4);
    expect(out.map((p) => p.isRest)).toEqual([false, false, false, true]);
  });

  it("wraps the microcycle and bumps the repetition", () => {
    const out = projectRotation(makeProgram(), makePosition({ current_slot_index: 3 }), 2);
    // The current slot keeps repetition 1; the wrap into the next pass bumps to 2.
    expect(out[0]!.repetition).toBe(1);
    expect(out[1]!.repetition).toBe(2);
  });

  it("enters a deload microcycle after the Nth repetition when auto_deload", () => {
    const program = makeProgram({ auto_deload: true });
    // Last repetition (4 of 4), last slot of the microcycle.
    const out = projectRotation(
      program,
      makePosition({ current_slot_index: 3, current_repetition: 4 }),
      3,
    );
    expect(out[0]!.isDeload).toBe(false);
    expect(out[0]!.repetition).toBe(4);
    // Wrap → deload microcycle (repetition null), then rolls into next meso.
    expect(out[1]!.isDeload).toBe(true);
    expect(out[1]!.repetition).toBeNull();
  });

  it("rolls deload into the next mesocycle at repetition 1", () => {
    const program = makeProgram({ auto_deload: true, days: [slot(0, "Full body")] });
    const out = projectRotation(
      program,
      makePosition({ current_slot_index: 0, current_repetition: 4, in_deload: true }),
      2,
    );
    expect(out[0]!.isDeload).toBe(true);
    expect(out[1]!.isDeload).toBe(false);
    expect(out[1]!.repetition).toBe(1);
  });

  it("skips the deload when auto_deload is off and wraps to repetition 1", () => {
    const program = makeProgram({ auto_deload: false, days: [slot(0, "Full body")] });
    const out = projectRotation(
      program,
      makePosition({ current_slot_index: 0, current_repetition: 4 }),
      2,
    );
    expect(out[0]!.repetition).toBe(4);
    expect(out[1]!.repetition).toBe(1);
    expect(out.every((p) => !p.isDeload)).toBe(true);
  });

  it("returns nothing for a rest-only program", () => {
    const program = makeProgram({ days: [slot(0, "Rest", true)] });
    expect(projectRotation(program, makePosition(), 5)).toEqual([]);
  });

  it("returns nothing when the program has no slots", () => {
    expect(projectRotation(makeProgram({ days: [] }), makePosition(), 5)).toEqual([]);
  });

  it("falls back to the first slot when the position index is out of range", () => {
    const out = projectRotation(makeProgram(), makePosition({ current_slot_index: 99 }), 2);
    expect(out[0]!.slot.name).toBe("Push");
  });
});

describe("groupByCycle", () => {
  it("groups consecutive slots into Cycle runs", () => {
    const out = projectRotation(makeProgram(), makePosition(), 8);
    const cycles = groupByCycle(out, 4);
    expect(cycles).toHaveLength(2);
    expect(cycles[0]!.repetition).toBe(1);
    expect(cycles[0]!.slots).toHaveLength(4);
    expect(cycles[1]!.repetition).toBe(2);
    expect(cycles.every((c) => c.mesocycleLength === 4)).toBe(true);
  });

  it("splits out the deload microcycle as its own group", () => {
    const program = makeProgram({ auto_deload: true, days: [slot(0, "Full body")] });
    const out = projectRotation(
      program,
      makePosition({ current_slot_index: 0, current_repetition: 4 }),
      3,
    );
    const cycles = groupByCycle(out, 4);
    expect(cycles.some((c) => c.isDeload)).toBe(true);
    const deload = cycles.find((c) => c.isDeload)!;
    expect(deload.repetition).toBeNull();
  });
});
