/**
 * T2 — drag-to-reorder exercises within an active workout session.
 *
 * Verifies that:
 *   1. Dragging an exercise to a new position calls `reorderExercise` with the
 *      correct global index.
 *   2. The rendered order reflects the change immediately (local mirror).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, waitFor } from "@testing-library/react";

import WorkoutDetailPage from "@/app/(app)/workouts/[id]/page";
import type { WorkoutExercise, WorkoutSession } from "@/lib/workouts/types";

// ---------------------------------------------------------------------------
// Hoisted shared state — available inside every vi.mock factory below.
// ---------------------------------------------------------------------------

/** Handlers captured when Reorder components render, exposed to test bodies. */
const captured = vi.hoisted(() => ({
  onReorder: null as null | ((items: WorkoutExercise[]) => void),
  dragEndHandlers: new Map<string, () => void>(),
}));

/** The mutation spy used by the mocked useReorderExercise hook. */
const reorderMutate = vi.hoisted(() => vi.fn());

/** Mutable session state read by the useSession mock at call time. */
const sessionState = vi.hoisted(
  () =>
    ({
      data: null,
      isLoading: true,
      isError: false,
    }) as { data: WorkoutSession | null; isLoading: boolean; isError: boolean },
);

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// motion/react — keep the real module for AnimatePresence, motion.div etc. so
// nested components (Sheet, InSessionActions) render correctly in jsdom; only
// replace Reorder.Group/Item to capture drag handlers, and stub useDragControls.
vi.mock("motion/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("motion/react")>();
  return {
    ...actual,
    Reorder: {
      ...actual.Reorder,
      Group: ({
        children,
        onReorder,
      }: {
        children: unknown;
        onReorder?: (v: WorkoutExercise[]) => void;
      }) => {
        captured.onReorder = onReorder ?? null;
        return children;
      },
      Item: ({
        children,
        value,
        onDragEnd,
      }: {
        children: unknown;
        value: WorkoutExercise;
        onDragEnd?: () => void;
      }) => {
        if (onDragEnd) captured.dragEndHandlers.set(value.id, onDragEnd);
        return children;
      },
    },
    useDragControls: () => ({ start: () => {} }),
  };
});

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "s1" }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("@/lib/hooks/workouts", () => ({
  useSession: vi.fn(() => sessionState),
  useReorderExercise: vi.fn(() => ({ mutate: reorderMutate, isPending: false })),
  useAddExercise: vi.fn(() => ({ mutate: vi.fn() })),
  useAddSet: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}) })),
  useUpdateSet: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}) })),
  useDeleteSet: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}) })),
  useRemoveExercise: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}) })),
  useFinishSession: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useSkipSession: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useSwapExercise: vi.fn(() => ({ mutate: vi.fn() })),
  useUpdateWorkoutExercise: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/hooks/me", () => ({
  useMe: vi.fn(() => ({ data: { unit_system: "metric", default_rest_seconds: 90 } })),
  useUpdateDefaultRest: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/hooks/exercises", () => ({
  useExerciseMeta: vi.fn(() => ({ data: new Map() })),
}));

vi.mock("@/lib/hooks/in-session-program", () => ({
  useSessionProgramContext: vi.fn(() => ({
    resolved: true,
    program: null,
    slot: null,
    slotExerciseFor: () => null,
  })),
  useChangeProgramTargets: vi.fn(() => ({ mutate: vi.fn() })),
  useSwapInProgram: vi.fn(() => ({ mutate: vi.fn() })),
  useRemoveFromProgram: vi.fn(() => ({ mutate: vi.fn() })),
}));

// Web Audio API is absent in jsdom.
vi.mock("@/lib/audio/unlock", () => ({ playTone: vi.fn() }));

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

function makeWE(id: string, position: number): WorkoutExercise {
  return {
    id,
    exercise_id: `ex-${position + 1}`,
    block_kind: "working",
    block_label: null,
    notes: null,
    position,
    substituted_for_exercise_id: null,
    sets: [],
  };
}

const WE1 = makeWE("we-1", 0);
const WE2 = makeWE("we-2", 1);
const WE3 = makeWE("we-3", 2);

const SESSION: WorkoutSession = {
  id: "s1",
  name: "Test Workout",
  started_at: "2026-01-01T00:00:00Z",
  ended_at: null,
  scheduled_workout_id: null,
  bodyweight_kg: null,
  notes: null,
  perceived_exertion: null,
  workout_exercises: [WE1, WE2, WE3],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Session exercise reorder (T2)", () => {
  beforeEach(() => {
    // Switch useSession to return a live in-progress session.
    sessionState.data = SESSION;
    sessionState.isLoading = false;
    sessionState.isError = false;

    // Clear captured handlers and the mutation spy between tests.
    captured.onReorder = null;
    captured.dragEndHandlers.clear();
    reorderMutate.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("calls reorderExercise with position 0 when exercise at index 2 is moved to the top", async () => {
    render(<WorkoutDetailPage />);

    // Wait until the local mirror syncs and all three cards are rendered.
    await waitFor(() => {
      expect(document.querySelectorAll("[data-workout-exercise-id]")).toHaveLength(3);
    });

    // Simulate Reorder.Group firing onReorder: move we-3 to front.
    act(() => {
      captured.onReorder?.([WE3, WE1, WE2]);
    });

    // Trigger drag-end for the moved exercise. localExercisesRef.current was
    // updated synchronously by handleBlockReorder, so findIndex returns 0.
    captured.dragEndHandlers.get("we-3")?.();

    expect(reorderMutate).toHaveBeenCalledTimes(1);
    expect(reorderMutate).toHaveBeenCalledWith({ workoutExerciseId: "we-3", position: 0 });
  });

  it("renders exercises in the new order after a drag", async () => {
    render(<WorkoutDetailPage />);

    await waitFor(() => {
      expect(document.querySelectorAll("[data-workout-exercise-id]")).toHaveLength(3);
    });

    // Confirm initial order before drag.
    let cards = document.querySelectorAll("[data-workout-exercise-id]");
    expect(cards[0]?.getAttribute("data-workout-exercise-id")).toBe("we-1");
    expect(cards[2]?.getAttribute("data-workout-exercise-id")).toBe("we-3");

    // Move we-3 to the front.
    act(() => {
      captured.onReorder?.([WE3, WE1, WE2]);
    });

    // The local mirror re-renders; verify the DOM order updated.
    await waitFor(() => {
      cards = document.querySelectorAll("[data-workout-exercise-id]");
      expect(cards[0]?.getAttribute("data-workout-exercise-id")).toBe("we-3");
      expect(cards[1]?.getAttribute("data-workout-exercise-id")).toBe("we-1");
      expect(cards[2]?.getAttribute("data-workout-exercise-id")).toBe("we-2");
    });
  });
});
