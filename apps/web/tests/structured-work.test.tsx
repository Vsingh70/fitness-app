import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { IntervalTimer } from "@/components/workouts/interval-timer";
import { SegmentEditor } from "@/components/workouts/segment-editor";
import { blockCountsAsVolume, isStructuredSetType, sumSegmentReps } from "@/lib/workouts/types";

// playTone reaches into AudioContext; stub the audio module so timers stay pure.
vi.mock("@/lib/audio/unlock", () => ({ playTone: vi.fn() }));

describe("structured-work type helpers", () => {
  it("sums reps across mini_set segments only", () => {
    const total = sumSegmentReps([
      { kind: "mini_set", reps: 10 },
      { kind: "rest", reps: null },
      { kind: "mini_set", reps: 3 },
      { kind: "mini_set", reps: 2 },
    ]);
    expect(total).toBe(15);
  });

  it("flags myo_rep / cluster as structured but not interval", () => {
    expect(isStructuredSetType("myo_rep")).toBe(true);
    expect(isStructuredSetType("cluster")).toBe(true);
    expect(isStructuredSetType("interval")).toBe(false);
    expect(isStructuredSetType("working")).toBe(false);
  });

  it("only the working block counts as volume", () => {
    expect(blockCountsAsVolume("working")).toBe(true);
    expect(blockCountsAsVolume("warmup")).toBe(false);
    expect(blockCountsAsVolume("cooldown")).toBe(false);
  });
});

describe("SegmentEditor", () => {
  it("logs a 10+3+2 myo-rep set whose total reps sum the bouts", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SegmentEditor onSubmit={onSubmit} />);

    // Two bouts seed by default; add a third for 10+3+2.
    await user.click(screen.getByRole("button", { name: /bout \(rest-pause\)/i }));

    await user.type(screen.getByLabelText("Reps for bout 1"), "10");
    await user.type(screen.getByLabelText("Reps for bout 2"), "3");
    await user.type(screen.getByLabelText("Reps for bout 3"), "2");

    expect(screen.getByTestId("segment-total")).toHaveTextContent("15");

    await user.click(screen.getByRole("button", { name: /save myo-rep/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0]![0];
    expect(payload.set_type).toBe("myo_rep");
    expect(payload.reps).toBe(15);
    expect(payload.segments).toHaveLength(3);
    expect(payload.segments.map((s: { reps: number }) => s.reps)).toEqual([10, 3, 2]);
    expect(payload.segments.every((s: { kind: string }) => s.kind === "mini_set")).toBe(true);
  });

  it("rejects fewer than two bouts", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SegmentEditor onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText("Reps for bout 1"), "10");
    await user.click(screen.getByRole("button", { name: /save myo-rep/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/at least two bouts/i);
  });
});

describe("IntervalTimer", () => {
  let clock = 0;
  const now = () => clock;

  beforeEach(() => {
    clock = 0;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts down work, advances to rest, and completes the final round", () => {
    const onComplete = vi.fn();
    render(
      <IntervalTimer
        rounds={1}
        workSeconds={3}
        restSeconds={2}
        onComplete={onComplete}
        now={now}
      />,
    );

    // Press start.
    act(() => {
      screen.getByRole("button", { name: /start intervals/i }).click();
    });
    expect(screen.getByText("Work")).toBeInTheDocument();

    // Burn the 3s work phase → flips to rest.
    act(() => {
      clock = 3100;
      vi.advanceTimersByTime(100);
    });
    expect(screen.getByText("Rest")).toBeInTheDocument();
    expect(onComplete).not.toHaveBeenCalled();

    // Burn the 2s rest phase → final round done.
    act(() => {
      clock = 5200;
      vi.advanceTimersByTime(100);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Intervals complete")).toBeInTheDocument();
  });
});
