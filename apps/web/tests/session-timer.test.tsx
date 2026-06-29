import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";

import { SessionTimer } from "@/components/workouts/session-timer";

/**
 * Focused test for SessionTimer locking the interval-based tick behavior
 * introduced in FIX 1 (rAF loop → setInterval(1000)).
 *
 * Uses vi.useFakeTimers() so the interval fires synchronously under act(),
 * making the test deterministic without real-time waits.
 */
describe("SessionTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("displays 0:00 initially for an in-progress session and advances to 0:03 after 3 s", () => {
    const startedAtMs = Date.now(); // fake-clock time

    render(<SessionTimer startedAtMs={startedAtMs} />);

    // Initial display: 0 elapsed seconds.
    expect(screen.getByRole("timer")).toHaveTextContent("0:00");

    // Advance the fake clock by 3 seconds; the interval fires 3 times.
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByRole("timer")).toHaveTextContent("0:03");
  });

  it("does not throw on mount or unmount", () => {
    const startedAtMs = Date.now();
    expect(() => {
      const { unmount } = render(<SessionTimer startedAtMs={startedAtMs} />);
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      unmount();
    }).not.toThrow();
  });

  it("shows the fixed elapsed time for a finished session (no timer runs)", () => {
    const startedAtMs = Date.now();
    const endedAtMs = startedAtMs + 5000; // 5 s elapsed

    render(<SessionTimer startedAtMs={startedAtMs} endedAtMs={endedAtMs} />);

    // Should show 0:05 and remain there even if time advances.
    expect(screen.getByRole("timer")).toHaveTextContent("0:05");

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    // Still 0:05 — the interval is not started for finished sessions.
    expect(screen.getByRole("timer")).toHaveTextContent("0:05");
  });
});
