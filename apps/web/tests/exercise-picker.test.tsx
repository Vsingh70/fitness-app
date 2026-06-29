import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// ---------------------------------------------------------------------------
// Module mocks (hoisted automatically by Vitest)
// ---------------------------------------------------------------------------

// Spy on the workouts API search function so we can assert filter args when
// the full ExercisePicker component is rendered.
const searchExercisesSpy = vi.fn().mockResolvedValue({ items: [], next_cursor: null });

vi.mock("@/lib/api/workouts", () => ({
  searchExercises: (...args: unknown[]) => searchExercisesSpy(...args),
}));

// Prevent CreateExerciseSheet from pulling in unrelated deps in this test file.
vi.mock("@/components/exercise/create-exercise-sheet", () => ({
  CreateExerciseSheet: () => null,
}));

// ---------------------------------------------------------------------------
// Imports (resolved after mocks are in place)
// ---------------------------------------------------------------------------

import {
  ExercisePicker,
  ExerciseResults,
  ExerciseRow,
} from "@/components/workouts/exercise-picker";
import type { Exercise } from "@/lib/workouts/types";

const NOOP = () => {};

function exercise(overrides: Partial<Exercise> = {}): Exercise {
  return {
    id: "e1",
    slug: "overhead-press",
    name: "Overhead Press",
    primary_muscle: "front_delts",
    secondary_muscles: [],
    equipment: "barbell",
    movement_pattern: "vertical_push",
    tracking_type: "weight_reps",
    is_unilateral: false,
    owner_id: null,
    archived_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function Providers({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ExerciseRow", () => {
  it("formats snake_case muscle / equipment / tracking labels for display", () => {
    render(<ExerciseRow exercise={exercise()} onPick={NOOP} />);
    expect(screen.getByText(/Front Delts/)).toBeInTheDocument();
    expect(screen.getByText(/Barbell/)).toBeInTheDocument();
    expect(screen.getByText("Weight Reps")).toBeInTheDocument();
    // The raw snake_case value must not leak into the UI.
    expect(screen.queryByText(/front_delts/)).toBeNull();
  });

  it("calls onPick with the exercise when clicked", () => {
    const onPick = vi.fn();
    render(<ExerciseRow exercise={exercise({ id: "x" })} onPick={onPick} />);
    screen.getByRole("button").click();
    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ id: "x" }));
  });
});

/**
 * Windowing guard (same approach as tests/perf/virtualization.test.tsx): jsdom
 * reports every box as 0 and react-virtual renders zero rows on a zero-height
 * viewport, so stub the layout box to a fixed height before rendering.
 */
describe("ExerciseResults windowing", () => {
  const VIEWPORT_PX = 600;
  let offsetHeightDescriptor: PropertyDescriptor | undefined;
  let originalGetBoundingClientRect: typeof Element.prototype.getBoundingClientRect;

  beforeEach(() => {
    offsetHeightDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight");
    originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get() {
        return VIEWPORT_PX;
      },
    });
    Element.prototype.getBoundingClientRect = function getBoundingClientRect(): DOMRect {
      return {
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: VIEWPORT_PX,
        bottom: VIEWPORT_PX,
        width: VIEWPORT_PX,
        height: VIEWPORT_PX,
        toJSON: () => ({}),
      } as DOMRect;
    };
  });

  afterEach(() => {
    if (offsetHeightDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetHeightDescriptor);
    } else {
      delete (HTMLElement.prototype as unknown as Record<string, unknown>).offsetHeight;
    }
    Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
  });

  it("mounts only a small window of a 200-item list, not every row", () => {
    const items = Array.from({ length: 200 }, (_, i) =>
      exercise({ id: `e${i}`, name: `Exercise ${i}` }),
    );
    const { container } = render(<ExerciseResults items={items} onPick={NOOP} />);

    const mounted = container.querySelectorAll("button").length;
    expect(mounted).toBeGreaterThan(0);
    // 600px viewport / 64px rows + overscan windows well under this cap; a
    // regression to rows.map over all items would mount 200.
    expect(mounted).toBeLessThanOrEqual(40);
  });

  it("requests the next page when the end of a short list is in view", () => {
    const onEndReached = vi.fn();
    const items = Array.from({ length: 10 }, (_, i) => exercise({ id: `e${i}` }));
    render(<ExerciseResults items={items} onPick={NOOP} hasNextPage onEndReached={onEndReached} />);
    expect(onEndReached).toHaveBeenCalled();
  });

  it("does not request more when there is no next page", () => {
    const onEndReached = vi.fn();
    const items = Array.from({ length: 10 }, (_, i) => exercise({ id: `e${i}` }));
    render(
      <ExerciseResults
        items={items}
        onPick={NOOP}
        hasNextPage={false}
        onEndReached={onEndReached}
      />,
    );
    expect(onEndReached).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// ExercisePicker movement_pattern filter
// ---------------------------------------------------------------------------

describe("ExercisePicker movement_pattern filter", () => {
  afterEach(() => {
    searchExercisesSpy.mockClear();
  });

  it("renders Mobility and Plyometric chips in the movement_pattern row", () => {
    render(<ExercisePicker open onOpenChange={NOOP} onPick={NOOP} />, {
      wrapper: Providers,
    });
    expect(screen.getByRole("button", { name: "Mobility" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Plyometric" })).toBeInTheDocument();
  });

  it("selecting Mobility drives the query with movement_pattern='mobility'", async () => {
    const user = userEvent.setup();
    render(<ExercisePicker open onOpenChange={NOOP} onPick={NOOP} />, {
      wrapper: Providers,
    });

    await user.click(screen.getByRole("button", { name: "Mobility" }));

    await waitFor(() => {
      expect(searchExercisesSpy).toHaveBeenCalledWith(
        undefined,
        expect.objectContaining({ movement_pattern: "mobility" }),
      );
    });
  });

  it("initialMovementPattern seeds the filter when the picker opens", async () => {
    render(
      <ExercisePicker open onOpenChange={NOOP} onPick={NOOP} initialMovementPattern="mobility" />,
      { wrapper: Providers },
    );

    await waitFor(() => {
      expect(searchExercisesSpy).toHaveBeenCalledWith(
        undefined,
        expect.objectContaining({ movement_pattern: "mobility" }),
      );
    });
  });
});
