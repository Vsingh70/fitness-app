/**
 * Tests for the movement_pattern filter row added to ExerciseLibrary (T4b Part A).
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
