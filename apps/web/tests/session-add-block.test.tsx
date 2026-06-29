/**
 * T4b Part B — Add warm-up / cooldown block affordance in the session page.
 *
 * Verifies that:
 *   1. "Add warm-up" opens the picker and addExercise is called with block_kind='warmup'
 *   2. "Add cooldown" → block_kind='cooldown'
 *   3. Plain "Add exercise" → block_kind='working'
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ---------------------------------------------------------------------------
// Hoisted shared state
// ---------------------------------------------------------------------------

/** Mutate spy captured for useAddExercise assertions. */
const addExerciseMutate = vi.hoisted(() => vi.fn());

/** Mutable session state controlled by each test. */
const sessionState = vi.hoisted(
  () =>
    ({
      data: null,
      isLoading: true,
      isError: false,
    }) as { data: unknown; isLoading: boolean; isError: boolean },
);

/**
 * Captured onPick callback from the mocked ExercisePicker.
 * Set each time the component renders with open=true.
 */
const capturedPick = vi.hoisted(
  () =>
    ({
      fn: null,
    }) as { fn: null | ((ex: { id: string }) => void) },
);

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("motion/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("motion/react")>();
  return {
    ...actual,
    Reorder: {
      ...actual.Reorder,
      Group: ({ children }: { children: unknown }) => children,
      Item: ({ children }: { children: unknown }) => children,
    },
    useDragControls: () => ({ start: () => {} }),
  };
});

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "s1" }),
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock next/dynamic so ExercisePicker captures its onPick prop but renders null.
vi.mock("next/dynamic", () => ({
  default: () =>
    function MockPicker(props: {
      open: boolean;
      onPick: (ex: { id: string }) => void;
      onOpenChange: (v: boolean) => void;
    }) {
      if (props.open) capturedPick.fn = props.onPick;
      return null;
    },
}));

vi.mock("@/lib/hooks/workouts", () => ({
  useSession: vi.fn(() => sessionState),
  useReorderExercise: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAddExercise: vi.fn(() => ({ mutate: addExerciseMutate })),
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

vi.mock("@/lib/audio/unlock", () => ({ playTone: vi.fn() }));

// ---------------------------------------------------------------------------
// Imports (resolved after mocks)
// ---------------------------------------------------------------------------

import WorkoutDetailPage from "@/app/(app)/workouts/[id]/page";
import type { WorkoutSession } from "@/lib/workouts/types";

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

const SESSION: WorkoutSession = {
  id: "s1",
  name: "Test Workout",
  started_at: "2026-01-01T00:00:00Z",
  ended_at: null,
  scheduled_workout_id: null,
  bodyweight_kg: null,
  notes: null,
  perceived_exertion: null,
  workout_exercises: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Session add block kind (T4b Part B)", () => {
  beforeEach(() => {
    sessionState.data = SESSION;
    sessionState.isLoading = false;
    sessionState.isError = false;
    capturedPick.fn = null;
    addExerciseMutate.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Add warm-up and Add cooldown buttons for active sessions", async () => {
    render(<WorkoutDetailPage />);
    await waitFor(() => {
      expect(screen.getByTestId("add-warmup")).toBeInTheDocument();
      expect(screen.getByTestId("add-cooldown")).toBeInTheDocument();
    });
  });

  it("Add warm-up → addExercise called with block_kind='warmup'", async () => {
    const user = userEvent.setup();
    render(<WorkoutDetailPage />);

    await waitFor(() => screen.getByTestId("add-warmup"));
    await user.click(screen.getByTestId("add-warmup"));

    // After the click, the picker is open and capturedPick.fn is set.
    await waitFor(() => expect(capturedPick.fn).not.toBeNull());

    act(() => {
      capturedPick.fn!({ id: "ex-new" });
    });

    expect(addExerciseMutate).toHaveBeenCalledWith(
      expect.objectContaining({ exercise_id: "ex-new", block_kind: "warmup" }),
    );
  });

  it("Add cooldown → addExercise called with block_kind='cooldown'", async () => {
    const user = userEvent.setup();
    render(<WorkoutDetailPage />);

    await waitFor(() => screen.getByTestId("add-cooldown"));
    await user.click(screen.getByTestId("add-cooldown"));

    await waitFor(() => expect(capturedPick.fn).not.toBeNull());

    act(() => {
      capturedPick.fn!({ id: "ex-new" });
    });

    expect(addExerciseMutate).toHaveBeenCalledWith(
      expect.objectContaining({ exercise_id: "ex-new", block_kind: "cooldown" }),
    );
  });

  it("plain Add exercise → addExercise called with block_kind='working'", async () => {
    const user = userEvent.setup();
    render(<WorkoutDetailPage />);

    await waitFor(() => screen.getByTestId("add-exercise"));
    await user.click(screen.getByTestId("add-exercise"));

    await waitFor(() => expect(capturedPick.fn).not.toBeNull());

    act(() => {
      capturedPick.fn!({ id: "ex-new" });
    });

    expect(addExerciseMutate).toHaveBeenCalledWith(
      expect.objectContaining({ exercise_id: "ex-new", block_kind: "working" }),
    );
  });
});
