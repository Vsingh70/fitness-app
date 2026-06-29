/**
 * Tests for the ExerciseLibrary component.
 * Covers: movement_pattern filter, item rendering with virtualized grid,
 * and navigation links.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ---------------------------------------------------------------------------
// Module mocks (hoisted automatically by Vitest)
// ---------------------------------------------------------------------------

const mockUseInfiniteExercises = vi.fn().mockReturnValue({
  data: { pages: [{ items: [], next_cursor: null }] },
  isLoading: false,
  isError: false,
  hasNextPage: false,
  fetchNextPage: vi.fn(),
  isFetchingNextPage: false,
});

vi.mock("@/lib/hooks/exercises", () => ({
  useInfiniteExercises: (...args: unknown[]) => mockUseInfiniteExercises(...args),
}));

vi.mock("@/components/exercise/create-exercise-sheet", () => ({
  CreateExerciseSheet: () => null,
}));

// ---------------------------------------------------------------------------
// Imports (resolved after mocks are in place)
// ---------------------------------------------------------------------------

import { ExerciseLibrary } from "@/components/exercise/exercise-library";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeExercise(overrides: {
  id: string;
  name: string;
  primary_muscle?: string;
  equipment?: string;
  owner_id?: string | null;
}) {
  return {
    id: overrides.id,
    slug: overrides.id,
    name: overrides.name,
    primary_muscle: overrides.primary_muscle ?? "chest",
    secondary_muscles: [],
    equipment: overrides.equipment ?? "barbell",
    movement_pattern: "horizontal_push",
    tracking_type: "weight_reps",
    is_unilateral: false,
    owner_id: overrides.owner_id ?? null,
    archived_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("ExerciseLibrary movement_pattern filter row", () => {
  afterEach(() => {
    mockUseInfiniteExercises.mockClear();
  });

  it("renders the Pattern filter row with Mobility and Plyometric chips", () => {
    render(<ExerciseLibrary showHeader={false} />);
    expect(screen.getByRole("button", { name: "Mobility" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Plyometric" })).toBeInTheDocument();
  });

  it("selecting Mobility updates the query with movement_pattern='mobility'", async () => {
    const user = userEvent.setup();
    render(<ExerciseLibrary showHeader={false} />);

    await user.click(screen.getByRole("button", { name: "Mobility" }));

    expect(mockUseInfiniteExercises).toHaveBeenLastCalledWith(
      expect.objectContaining({ movement_pattern: "mobility" }),
    );
  });

  it("selecting All after Mobility clears the movement_pattern filter", async () => {
    const user = userEvent.setup();
    render(<ExerciseLibrary showHeader={false} />);

    await user.click(screen.getByRole("button", { name: "Mobility" }));
    // The "All" chip in the Pattern row — note there are also "All" and "Mine"
    // scope tabs, so we click by finding the button that un-sets the pattern.
    // After selecting Mobility the Mobility chip is active; clicking All resets.
    const allButtons = screen.getAllByRole("button", { name: "All" });
    // The Pattern filter row "All" chip is the last "All" button in the filter area.
    // We confirm by asserting the subsequent hook call omits movement_pattern.
    await user.click(allButtons[allButtons.length - 1]!);

    expect(mockUseInfiniteExercises).toHaveBeenLastCalledWith(
      expect.not.objectContaining({ movement_pattern: expect.anything() }),
    );
  });

  it("initially calls useInfiniteExercises without a movement_pattern", () => {
    render(<ExerciseLibrary showHeader={false} />);
    expect(mockUseInfiniteExercises).toHaveBeenLastCalledWith(
      expect.not.objectContaining({ movement_pattern: expect.anything() }),
    );
  });
});

describe("ExerciseLibrary grid rendering", () => {
  afterEach(() => {
    mockUseInfiniteExercises.mockClear();
  });

  it("renders cards for a small dataset with correct navigation links", () => {
    const items = [
      makeExercise({ id: "ex-1", name: "Bench Press" }),
      makeExercise({ id: "ex-2", name: "Overhead Press" }),
      makeExercise({ id: "ex-3", name: "Leg Press" }),
      makeExercise({ id: "ex-4", name: "Deadlift" }),
    ];
    mockUseInfiniteExercises.mockReturnValue({
      data: { pages: [{ items, next_cursor: null }] },
      isLoading: false,
      isError: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<ExerciseLibrary showHeader={false} />);

    // All four exercises should be visible (4 items = 2 rows × 2 cols, all
    // within the jsdom viewport height so the virtualizer mounts all rows).
    expect(screen.getByText("Bench Press")).toBeInTheDocument();
    expect(screen.getByText("Overhead Press")).toBeInTheDocument();
    expect(screen.getByText("Leg Press")).toBeInTheDocument();
    expect(screen.getByText("Deadlift")).toBeInTheDocument();

    // Navigation links must exist and point to the exercise detail pages.
    expect(screen.getByRole("link", { name: /Bench Press/i })).toHaveAttribute(
      "href",
      "/exercises/ex-1",
    );
    expect(screen.getByRole("link", { name: /Leg Press/i })).toHaveAttribute(
      "href",
      "/exercises/ex-3",
    );
  });

  it("shows 'Load more' button when there are more pages", () => {
    const items = [makeExercise({ id: "ex-1", name: "Bench Press" })];
    const fetchNextPage = vi.fn();
    mockUseInfiniteExercises.mockReturnValue({
      data: { pages: [{ items, next_cursor: "cursor-abc" }] },
      isLoading: false,
      isError: false,
      hasNextPage: true,
      fetchNextPage,
      isFetchingNextPage: false,
    });

    render(<ExerciseLibrary showHeader={false} />);

    expect(screen.getByRole("button", { name: "Load more" })).toBeInTheDocument();
  });

  it("shows empty-state message when no items match", () => {
    mockUseInfiniteExercises.mockReturnValue({
      data: { pages: [{ items: [], next_cursor: null }] },
      isLoading: false,
      isError: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<ExerciseLibrary showHeader={false} />);

    expect(screen.getByText(/No exercises match those filters/i)).toBeInTheDocument();
  });
});
