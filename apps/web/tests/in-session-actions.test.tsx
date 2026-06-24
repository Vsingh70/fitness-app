import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProgramTargetEditor } from "@/components/workouts/program-target-editor";
import type { ProgramDayExercise } from "@/lib/programs/types";

const PDE: ProgramDayExercise = {
  id: "pde-1",
  exercise_id: "ex-1",
  notes: null,
  position: 0,
  progression_strategy: "none",
  rep_mode: "range",
  rest_seconds: 120,
  target_sets: 3,
  target_reps_low: 8,
  target_reps_high: 12,
  target_rir_low: 1,
  target_rir_high: 2,
  target_rpe_low: null,
  target_rpe_high: null,
};

describe("ProgramTargetEditor (05 §3 — change in program)", () => {
  it("emits only the changed targets in the diff", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ProgramTargetEditor
        pde={PDE}
        intensityMode="rir"
        onSave={onSave}
        onCancel={() => undefined}
      />,
    );

    const sets = screen.getByLabelText("Target sets");
    await user.clear(sets);
    await user.type(sets, "4");

    await user.click(screen.getByRole("button", { name: /save to program/i }));

    expect(onSave).toHaveBeenCalledTimes(1);
    // Only target_sets changed; reps/intensity stay out of the patch.
    expect(onSave.mock.calls[0]![0]).toEqual({ target_sets: 4 });
  });

  it("clears a rep bound to null when emptied", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ProgramTargetEditor
        pde={PDE}
        intensityMode="rir"
        onSave={onSave}
        onCancel={() => undefined}
      />,
    );

    await user.clear(screen.getByLabelText("Reps high"));
    await user.click(screen.getByRole("button", { name: /save to program/i }));

    expect(onSave.mock.calls[0]![0]).toEqual({ target_reps_high: null });
  });

  it("writes RPE columns when the program is in RPE mode", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const rpePde: ProgramDayExercise = {
      ...PDE,
      target_rir_low: null,
      target_rir_high: null,
      target_rpe_low: "7",
      target_rpe_high: "8",
    };
    render(
      <ProgramTargetEditor
        pde={rpePde}
        intensityMode="rpe"
        onSave={onSave}
        onCancel={() => undefined}
      />,
    );

    const low = screen.getByLabelText("RPE low");
    await user.clear(low);
    await user.type(low, "8");
    await user.click(screen.getByRole("button", { name: /save to program/i }));

    expect(onSave.mock.calls[0]![0]).toEqual({ target_rpe_low: 8 });
  });
});
