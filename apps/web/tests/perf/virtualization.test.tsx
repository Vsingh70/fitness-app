import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import { MealList, type MealRowModel } from "@/components/nutrition/meal-list";
import type { FoodResponse } from "@/lib/api/nutrition";

/**
 * Boundedness guard for the windowed long lists.
 *
 * MealList (like the program library and food-search results) windows its rows
 * with `@tanstack/react-virtual` so a day with hundreds of meals mounts only the
 * handful of rows that fit the viewport — not every row. This test renders a
 * 200-row list and asserts the DOM holds only a small windowed subset.
 *
 * What it guards: a regression that removes the virtualizer (or reverts to a
 * plain `rows.map(...)`) would mount all 200 MealRows — `<section>` count would
 * jump to 200 and this test would fail, flagging the lost windowing.
 *
 * jsdom reports every element's box as 0, and react-virtual renders ZERO rows on
 * a zero-height viewport. We stub the layout box (offsetHeight + bounding rect)
 * to a fixed height BEFORE rendering so the virtualizer computes a real, bounded
 * window, and restore the originals afterwards.
 */

const VIEWPORT_PX = 600;
// Fixed estimateSize in MealList is 132px; a 600px viewport + overscan(6) windows
// well under this cap, while a regression to "render all" would mount 200.
const MAX_MOUNTED_ROWS = 40;
const TOTAL_ROWS = 200;

const NOOP = () => {};

function makeRows(count: number): MealRowModel[] {
  return Array.from({ length: count }, (_, i) => ({
    key: `meal-${i}`,
    name: `Meal ${i}`,
    mealId: null,
    sourcePlanMealId: null,
    eatenAt: null,
    items: [],
    onAddFood: NOOP,
  }));
}

describe("virtualization boundedness", () => {
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

  it(`mounts a small window of a ${TOTAL_ROWS}-row MealList, not every row`, () => {
    const { container } = render(
      <MealList
        rows={makeRows(TOTAL_ROWS)}
        foodLookup={new Map<string, FoodResponse>()}
        onDeleteItem={NOOP}
        onEditItem={NOOP}
        onDeleteMeal={() => {}}
      />,
    );

    // MealRow's root element is a <section>; count how many actually mounted.
    const mounted = container.querySelectorAll("section").length;

    expect(
      mounted,
      `MealList mounted ${mounted} of ${TOTAL_ROWS} rows. The list is virtualized, ` +
        `so only a windowed subset should mount. A count near ${TOTAL_ROWS} means ` +
        `windowing regressed (e.g. reverted to rows.map over all rows).`,
    ).toBeGreaterThan(0);
    expect(mounted).toBeLessThanOrEqual(MAX_MOUNTED_ROWS);
  });
});
