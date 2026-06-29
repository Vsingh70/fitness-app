/**
 * Tests for two workout-page display bugs:
 *   BUG A — raw tracking_type enum leaked to the UI (now uses labelize())
 *   BUG B — weight hardcoded to kg, ignoring users.unit_system
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { NextUpPreview } from "@/components/workouts/next-up-preview";
import { ExerciseCard } from "@/components/workouts/exercise-card";
import { ReadOnlySessionView } from "@/components/workouts/read-only-session";
import { SetRow } from "@/components/workouts/set-row";
import { PrBanner } from "@/components/workouts/summary/pr-banner";
import { SetByExerciseTable } from "@/components/workouts/summary/set-by-exercise-table";
import type { WorkoutExercise, WorkoutSet, Exercise } from "@/lib/workouts/types";

// ---------------------------------------------------------------------------
// Minimal fixture helpers
// ---------------------------------------------------------------------------

function makeSet(overrides: Partial<WorkoutSet> = {}): WorkoutSet {
  return {
    id: "set-1",
    set_index: 0,
    set_type: "working",
    is_pr: false,
    weight_kg: null,
    reps: null,
    rpe: null,
    rir: null,
    distance_meters: null,
    duration_seconds: null,
    rounds: null,
    notes: null,
    segments: [],
    ...overrides,
  };
}

function makeWorkoutExercise(overrides: Partial<WorkoutExercise> = {}): WorkoutExercise {
  return {
    id: "we-1",
    exercise_id: "ex-1",
    block_kind: "working",
    block_label: null,
    notes: null,
    position: 0,
    substituted_for_exercise_id: null,
    sets: [],
    ...overrides,
  };
}

function makeExercise(overrides: Partial<Exercise> = {}): Exercise {
  return {
    id: "ex-1",
    name: "Squat",
    slug: "squat",
    tracking_type: "weight_reps",
    equipment: "barbell",
    movement_pattern: "squat",
    primary_muscle: "quads",
    secondary_muscles: [],
    is_unilateral: false,
    owner_id: null,
    archived_at: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// BUG A — labelize() wraps raw enum
// ---------------------------------------------------------------------------

describe("BUG A: tracking_type enum is humanised in the UI", () => {
  it("NextUpPreview shows 'Weight Reps' not 'weight_reps'", () => {
    render(<NextUpPreview name="Squat" trackingType="weight_reps" onSkipAhead={() => undefined} />);
    expect(screen.getByText(/Weight Reps/)).toBeInTheDocument();
    expect(screen.queryByText("weight_reps")).toBeNull();
  });

  it("ExerciseCard shows 'Weight Reps' not 'weight_reps' in the tracking pill", () => {
    const we = makeWorkoutExercise();
    render(
      <ExerciseCard
        workoutExercise={we}
        exerciseName="Squat"
        trackingType="weight_reps"
        onAddSet={vi.fn()}
        onDeleteSet={vi.fn()}
        onRemoveExercise={vi.fn()}
      />,
    );
    // The pill should render the human label
    expect(screen.getByText("Weight Reps")).toBeInTheDocument();
    expect(screen.queryByText("weight_reps")).toBeNull();
  });

  it("ReadOnlySessionView shows 'Weight Reps' not 'weight_reps' in the tracking pill", () => {
    const we = makeWorkoutExercise({ exercise_id: "ex-1" });
    const meta = new Map<string, Exercise>([
      ["ex-1", makeExercise({ tracking_type: "weight_reps" })],
    ]);
    render(<ReadOnlySessionView workoutExercises={[we]} exerciseMeta={meta} />);
    expect(screen.getByText("Weight Reps")).toBeInTheDocument();
    expect(screen.queryByText("weight_reps")).toBeNull();
  });

  it("ExerciseCard shows 'Bodyweight Reps' not 'bodyweight_reps'", () => {
    const we = makeWorkoutExercise();
    render(
      <ExerciseCard
        workoutExercise={we}
        exerciseName="Push-up"
        trackingType="bodyweight_reps"
        onAddSet={vi.fn()}
        onDeleteSet={vi.fn()}
        onRemoveExercise={vi.fn()}
      />,
    );
    expect(screen.getByText("Bodyweight Reps")).toBeInTheDocument();
    expect(screen.queryByText("bodyweight_reps")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BUG B — weight respects unit_system
// ---------------------------------------------------------------------------

describe("BUG B: SetRow respects unit_system", () => {
  it("metric: weight input shows kg value, commit sends same kg string", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SetRow trackingType="weight_reps" setIndex={0} onSubmit={onSubmit} unit="metric" />);
    // Label stays "kg"
    await user.type(screen.getByLabelText("kg for set 1"), "100");
    await user.type(screen.getByLabelText("reps for set 1"), "5");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0]![0];
    expect(payload.weight_kg).toBe("100");
    expect(payload.reps).toBe(5);
  });

  it("imperial: weight input shows lb value pre-filled from kg initial", () => {
    render(
      <SetRow
        trackingType="weight_reps"
        setIndex={0}
        initial={{ weight_kg: "100", reps: "5" }}
        onSubmit={vi.fn()}
        unit="imperial"
      />,
    );
    // 100 kg → 220.5 lb (round1)
    const weightInput = screen.getByLabelText("lb for set 1") as HTMLInputElement;
    expect(weightInput.value).toBe("220.5");
  });

  it("imperial: committing a lb value sends the correct kg back to the API", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SetRow trackingType="weight_reps" setIndex={0} onSubmit={onSubmit} unit="imperial" />);
    // User types in lb
    await user.type(screen.getByLabelText("lb for set 1"), "220.5");
    await user.type(screen.getByLabelText("reps for set 1"), "5");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0]![0];
    // 220.5 lb / 2.20462 ≈ 100.017... kg
    const sentKg = Number(payload.weight_kg);
    expect(sentKg).toBeCloseTo(100, 0); // within 1 kg of 100
  });

  it("imperial: column header shows 'lb' not 'kg'", () => {
    const we = makeWorkoutExercise();
    render(
      <ExerciseCard
        workoutExercise={we}
        exerciseName="Squat"
        trackingType="weight_reps"
        unit="imperial"
        onAddSet={vi.fn()}
        onDeleteSet={vi.fn()}
        onRemoveExercise={vi.fn()}
      />,
    );
    // There should be a "lb" column header and no "kg" column header
    expect(screen.getAllByText("lb").length).toBeGreaterThan(0);
    // The header row should NOT contain a standalone "kg" cell
    const headerCells = screen.queryAllByText("kg");
    expect(headerCells).toHaveLength(0);
  });
});

describe("BUG B: PrBanner weight display respects unit_system", () => {
  const PR_METRIC = {
    exerciseId: "ex-1",
    exerciseName: "Squat",
    weightKg: 100,
    reps: 5,
    estimated1Rm: 112.5,
  };

  it("metric: shows weight in kg with 'kg' label", () => {
    render(<PrBanner prs={[PR_METRIC]} unit="metric" />);
    expect(screen.getByText(/100 kg × 5/)).toBeInTheDocument();
    expect(screen.getByText(/112\.5 kg/)).toBeInTheDocument();
  });

  it("imperial: shows weight in lb with 'lb' label, not 'kg'", () => {
    render(<PrBanner prs={[PR_METRIC]} unit="imperial" />);
    // 100 kg → 220.5 lb, 112.5 kg → 248 lb (round1: 248.0)
    expect(screen.getByText(/220\.5 lb × 5/)).toBeInTheDocument();
    expect(screen.getByText(/248 lb/)).toBeInTheDocument();
    // Neither weight cell should contain "kg"
    expect(screen.queryByText(/\d+ kg/)).toBeNull();
  });
});

describe("BUG B: SetByExerciseTable weight display respects unit_system", () => {
  const set = makeSet({ weight_kg: "100", reps: 8, is_pr: false });
  const we = makeWorkoutExercise({ sets: [set] });
  const meta = new Map<string, Exercise>([["ex-1", makeExercise()]]);

  it("metric: weight column header shows 'Weight (kg)' and value shows '100'", () => {
    render(<SetByExerciseTable workoutExercises={[we]} exerciseMeta={meta} unit="metric" />);
    expect(screen.getByText("Weight (kg)")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "100" })).toBeInTheDocument();
  });

  it("imperial: weight column header shows 'Weight (lb)' and value shows '220.5'", () => {
    render(<SetByExerciseTable workoutExercises={[we]} exerciseMeta={meta} unit="imperial" />);
    expect(screen.getByText("Weight (lb)")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "220.5" })).toBeInTheDocument();
  });
});
