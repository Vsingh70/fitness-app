import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExerciseResults, ExerciseRow } from "@/components/workouts/exercise-picker";
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
});
