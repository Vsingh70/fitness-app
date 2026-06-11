import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";

import { RestTimer } from "@/components/workouts/rest-timer";

describe("RestTimer", () => {
  let clock = 0;
  const now = () => clock;

  beforeEach(() => {
    clock = 0;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts down and announces zero", async () => {
    const onComplete = vi.fn();
    render(<RestTimer seconds={3} onComplete={onComplete} now={now} />);
    expect(screen.getByRole("timer")).toHaveTextContent("3");

    act(() => {
      clock = 1500;
      vi.advanceTimersByTime(200);
    });
    expect(screen.getByRole("timer")).toHaveTextContent("2");

    act(() => {
      clock = 3100;
      vi.advanceTimersByTime(200);
    });

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("timer")).toHaveTextContent("0");
  });

  it("does not fire onComplete twice", async () => {
    const onComplete = vi.fn();
    render(<RestTimer seconds={1} onComplete={onComplete} now={now} />);
    act(() => {
      clock = 2000;
      vi.advanceTimersByTime(500);
    });
    act(() => {
      clock = 3000;
      vi.advanceTimersByTime(500);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
