import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import {
  collapseVariant,
  collapseVariants,
  useReducedMotionSafe,
} from "@/lib/motion/use-reduced-motion-safe";

// Hoisted mock so each test can drive motion's reduced-motion preference.
const { reducedRef } = vi.hoisted(() => ({ reducedRef: { current: false as boolean } }));

vi.mock("motion/react", () => ({
  useReducedMotion: () => reducedRef.current,
}));

afterEach(() => {
  reducedRef.current = false;
});

describe("collapseVariant", () => {
  it("drops transform keys but keeps opacity and other style", () => {
    const out = collapseVariant({ opacity: 0, y: 8, scale: 0.9, color: "red" });
    expect(out).toEqual({ opacity: 0, color: "red" });
  });

  it("passes through variants with no transforms unchanged", () => {
    expect(collapseVariant({ opacity: 1 })).toEqual({ opacity: 1 });
  });

  it("leaves non-object variants (resolvers) untouched", () => {
    const resolver = () => ({ opacity: 1, x: 4 });
    expect(collapseVariant(resolver)).toBe(resolver);
  });
});

describe("collapseVariants", () => {
  it("collapses every named variant to opacity-only", () => {
    const out = collapseVariants({
      hidden: { opacity: 0, y: 8 },
      visible: { opacity: 1, y: 0 },
    });
    expect(out).toEqual({ hidden: { opacity: 0 }, visible: { opacity: 1 } });
  });
});

describe("useReducedMotionSafe", () => {
  it("returns variants untouched when reduced motion is off", () => {
    reducedRef.current = false;
    const { result } = renderHook(() => useReducedMotionSafe());
    expect(result.current.reduced).toBe(false);

    const variants = {
      hidden: { opacity: 0, y: 8 },
      visible: { opacity: 1, y: 0 },
    };
    expect(result.current.safe(variants)).toEqual(variants);
  });

  it("collapses variants to opacity-only when reduced motion is on", () => {
    reducedRef.current = true;
    const { result } = renderHook(() => useReducedMotionSafe());
    expect(result.current.reduced).toBe(true);

    expect(
      result.current.safe({
        hidden: { opacity: 0, y: 8, scale: 0.96 },
        visible: { opacity: 1, y: 0, scale: 1 },
      }),
    ).toEqual({ hidden: { opacity: 0 }, visible: { opacity: 1 } });
  });
});
