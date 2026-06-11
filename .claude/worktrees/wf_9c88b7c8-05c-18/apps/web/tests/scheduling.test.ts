import { describe, expect, it } from "vitest";

import { chipColor, deloadTint, diffDays, reschedulePathSuffix } from "@/lib/scheduling/chip";

describe("chipColor", () => {
  it("returns distinct styles per status", () => {
    const planned = chipColor("planned");
    const inProgress = chipColor("in_progress");
    const completed = chipColor("completed");
    const skipped = chipColor("skipped");
    expect(new Set([planned, inProgress, completed, skipped]).size).toBe(4);
    expect(planned).toContain("accent");
    expect(completed).toContain("success");
    expect(skipped).toContain("text-tertiary");
  });
});

describe("deloadTint", () => {
  it("returns a ring class when deload, empty string otherwise", () => {
    expect(deloadTint(true)).toContain("ring");
    expect(deloadTint(false)).toBe("");
  });
});

describe("reschedulePathSuffix", () => {
  it("is empty when shift is 0 or undefined", () => {
    expect(reschedulePathSuffix()).toBe("");
    expect(reschedulePathSuffix(0)).toBe("");
  });
  it("encodes positive and negative shifts", () => {
    expect(reschedulePathSuffix(3)).toBe("?shift_remaining_days=3");
    expect(reschedulePathSuffix(-2)).toBe("?shift_remaining_days=-2");
  });
});

describe("diffDays", () => {
  it("counts forward across a month boundary", () => {
    expect(diffDays("2026-06-29", "2026-07-02")).toBe(3);
  });
  it("returns negative for moves backward", () => {
    expect(diffDays("2026-06-10", "2026-06-08")).toBe(-2);
  });
});
