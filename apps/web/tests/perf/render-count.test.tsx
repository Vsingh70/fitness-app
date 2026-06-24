import { Profiler, useCallback, useState } from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SetRow } from "@/components/workouts/set-row";

import { RENDER } from "./budgets";

/**
 * Re-render budget for a hot leaf component.
 *
 * SetRow is rendered many times per active workout (4-5 rows per exercise, several
 * exercises). The audit found zero React.memo in the codebase, so leaves re-render
 * whenever an unrelated ancestor updates. This test pins that cost: it gives SetRow
 * stable props, forces unrelated parent state changes, and counts how many times
 * SetRow actually re-commits (React Profiler "update" phase).
 *
 * It is a ratchet. Today SetRow is not memoized, so it re-renders on every parent
 * update and the budget reflects that. Wrapping SetRow in React.memo (with stable
 * props, as provided here) drops the count to 0, at which point the budget in
 * perf/budgets.json should be tightened to lock the win in.
 */

const BUMPS = 4;

function Harness({ onUpdate }: { onUpdate: () => void }) {
  const [n, setN] = useState(0);
  // Stable props: a memoized SetRow would correctly bail out on parent re-render.
  const onSubmit = useCallback(() => {}, []);
  return (
    <div>
      <button type="button" onClick={() => setN((x) => x + 1)}>
        bump {n}
      </button>
      <Profiler
        id="set-row"
        onRender={(_id, phase) => {
          if (phase === "update") onUpdate();
        }}
      >
        <SetRow trackingType="weight_reps" setIndex={0} onSubmit={onSubmit} />
      </Profiler>
    </div>
  );
}

describe("render-count budget (ratchet)", () => {
  it(`SetRow re-renders at most ${RENDER.setRowUnrelatedRerendersMax}x on ${BUMPS} unrelated parent updates`, async () => {
    const user = userEvent.setup();
    let updates = 0;
    render(<Harness onUpdate={() => (updates += 1)} />);

    const bump = screen.getByRole("button", { name: /bump/i });
    for (let i = 0; i < BUMPS; i += 1) {
      await user.click(bump);
    }

    expect(
      updates,
      `SetRow re-committed ${updates} time(s) on ${BUMPS} unrelated parent updates. ` +
        `Memoizing SetRow should bring this to 0; then tighten the budget.`,
    ).toBeLessThanOrEqual(RENDER.setRowUnrelatedRerendersMax);
  });
});
