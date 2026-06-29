import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ExerciseEditorRow } from "@/components/programs/exercise-editor-row";
import type { ProgramDayExercise } from "@/lib/programs/types";

function pde(overrides: Partial<ProgramDayExercise> = {}): ProgramDayExercise {
  return {
    id: "pde1",
    exercise_id: "ex1",
    position: 0,
    block_kind: "working",
    block_label: null,
    target_sets: 3,
    rep_mode: "range",
    target_reps_low: 8,
    target_reps_high: 12,
    target_rpe_low: null,
    target_rpe_high: null,
    target_rir_low: null,
    target_rir_high: null,
    rest_seconds: 90,
    progression_strategy: "none",
    notes: null,
    ...overrides,
  };
}

describe("ExerciseEditorRow — single intensity box", () => {
  it("writes both RPE bounds and accepts .5 steps", async () => {
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    render(
      <ExerciseEditorRow
        pde={pde()}
        name="Squat"
        intensityMode="rpe"
        onUpdate={onUpdate}
        onDelete={() => {}}
      />,
    );
    const input = screen.getByLabelText("RPE target");
    await user.clear(input);
    await user.type(input, "7.5");
    await user.tab();
    expect(onUpdate).toHaveBeenCalledWith({ target_rpe_low: 7.5, target_rpe_high: 7.5 });
  });

  it("writes both RIR bounds as whole numbers", async () => {
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    render(
      <ExerciseEditorRow
        pde={pde()}
        name="Squat"
        intensityMode="rir"
        onUpdate={onUpdate}
        onDelete={() => {}}
      />,
    );
    const input = screen.getByLabelText("RIR target");
    await user.clear(input);
    await user.type(input, "2");
    await user.tab();
    expect(onUpdate).toHaveBeenCalledWith({ target_rir_low: 2, target_rir_high: 2 });
  });

  it("hides the intensity box when intensity is Off", () => {
    render(
      <ExerciseEditorRow
        pde={pde()}
        name="Squat"
        intensityMode="off"
        onUpdate={() => {}}
        onDelete={() => {}}
      />,
    );
    expect(screen.queryByLabelText("RPE target")).toBeNull();
    expect(screen.queryByLabelText("RIR target")).toBeNull();
  });
});

describe("ExerciseEditorRow — block kind selector", () => {
  it("defaults to Working and does not call onUpdate when Working is already selected", async () => {
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    render(
      <ExerciseEditorRow
        pde={pde({ block_kind: "working" })}
        name="Squat"
        intensityMode="off"
        onUpdate={onUpdate}
        onDelete={() => {}}
      />,
    );
    // Working radio is checked by default
    const workingBtn = screen.getByRole("radio", { name: "Working" });
    expect(workingBtn).toHaveAttribute("aria-checked", "true");
    // Clicking the already-active option produces no update
    await user.click(workingBtn);
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("calls onUpdate with block_kind='cooldown' when Cooldown is selected", async () => {
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    render(
      <ExerciseEditorRow
        pde={pde({ block_kind: "working" })}
        name="Deadlift"
        intensityMode="off"
        onUpdate={onUpdate}
        onDelete={() => {}}
      />,
    );
    await user.click(screen.getByRole("radio", { name: "Cooldown" }));
    expect(onUpdate).toHaveBeenCalledWith({ block_kind: "cooldown" });
  });

  it("calls onUpdate with block_kind='warmup' when Warm-up is selected", async () => {
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    render(
      <ExerciseEditorRow
        pde={pde({ block_kind: "working" })}
        name="Band Pull-Apart"
        intensityMode="off"
        onUpdate={onUpdate}
        onDelete={() => {}}
      />,
    );
    await user.click(screen.getByRole("radio", { name: "Warm-up" }));
    expect(onUpdate).toHaveBeenCalledWith({ block_kind: "warmup" });
  });
});
