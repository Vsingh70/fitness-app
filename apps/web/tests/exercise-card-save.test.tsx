/**
 * Regression: "whenever I save a workout it just keeps adding sets".
 *
 * Root cause — every SetRow (including already-logged sets) had its Save wired
 * to onAddSet, so re-saving a logged set appended a duplicate instead of
 * updating it. Logged rows must update (onUpdateSet); only the trailing blank
 * entry row may add (onAddSet).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ExerciseCard } from "@/components/workouts/exercise-card";
import type { WorkoutExercise, WorkoutSet } from "@/lib/workouts/types";

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
    exercise_name: "Squat",
    tracking_type: "weight_reps",
    block_kind: "working",
    block_label: null,
    notes: null,
    position: 0,
    substituted_for_exercise_id: null,
    sets: [],
    ...overrides,
  };
}

describe("ExerciseCard: saving a set never duplicates it", () => {
  it("clicking Save on an already-logged set updates it (onUpdateSet), does NOT add", async () => {
    const user = userEvent.setup();
    const onAddSet = vi.fn();
    const onUpdateSet = vi.fn();
    const we = makeWorkoutExercise({ sets: [makeSet({ id: "set-1", weight_kg: "100", reps: 5 })] });

    render(
      <ExerciseCard
        workoutExercise={we}
        exerciseName="Squat"
        trackingType="weight_reps"
        unit="metric"
        onAddSet={onAddSet}
        onUpdateSet={onUpdateSet}
        onDeleteSet={vi.fn()}
        onRemoveExercise={vi.fn()}
      />,
    );

    // With one logged set, the add row is hidden → exactly one Save button.
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(onUpdateSet).toHaveBeenCalledTimes(1);
    expect(onUpdateSet.mock.calls[0]![0]).toBe("set-1");
    expect(onAddSet).not.toHaveBeenCalled();
  });

  it("the trailing blank entry row still adds a new set (onAddSet), not update", async () => {
    const user = userEvent.setup();
    const onAddSet = vi.fn();
    const onUpdateSet = vi.fn();
    const we = makeWorkoutExercise({ sets: [makeSet({ id: "set-1", weight_kg: "100", reps: 5 })] });

    render(
      <ExerciseCard
        workoutExercise={we}
        exerciseName="Squat"
        trackingType="weight_reps"
        unit="metric"
        onAddSet={onAddSet}
        onUpdateSet={onUpdateSet}
        onDeleteSet={vi.fn()}
        onRemoveExercise={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /add set/i }));

    const rows = screen.getAllByTestId("set-row");
    const blank = rows[rows.length - 1]!;
    await user.type(within(blank).getByLabelText("kg for set 2"), "110");
    await user.type(within(blank).getByLabelText("reps for set 2"), "5");
    await user.click(within(blank).getByRole("button", { name: /save/i }));

    expect(onAddSet).toHaveBeenCalledTimes(1);
    expect(onUpdateSet).not.toHaveBeenCalled();
  });
});
