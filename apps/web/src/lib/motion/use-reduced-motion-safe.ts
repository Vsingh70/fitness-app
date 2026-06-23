"use client";

import { useReducedMotion } from "motion/react";
import type { Target, TargetAndTransition, Variant, Variants } from "motion/react";

/**
 * Transform-ish style keys we strip under reduced motion. Anything that moves
 * the element in space; only opacity (and non-transform style) is allowed to
 * animate when the user has asked for reduced motion.
 */
const TRANSFORM_KEYS = [
  "x",
  "y",
  "z",
  "scale",
  "scaleX",
  "scaleY",
  "rotate",
  "rotateX",
  "rotateY",
  "rotateZ",
  "skewX",
  "skewY",
  "translateX",
  "translateY",
  "translateZ",
] as const satisfies readonly (keyof Target)[];

function isObjectVariant(value: unknown): value is TargetAndTransition {
  return typeof value === "object" && value !== null;
}

/**
 * Heuristic: a `Variants` map's values are themselves variants (objects or
 * resolver functions), whereas a single `TargetAndTransition`'s values are
 * animatable primitives/arrays. Used to disambiguate the two shapes at runtime
 * since they're structurally both plain objects.
 */
function looksLikeVariantsMap(input: object): input is Variants {
  const values = Object.values(input);
  if (values.length === 0) return false;
  return values.every(
    (v) => typeof v === "function" || (typeof v === "object" && v !== null && !Array.isArray(v)),
  );
}

/**
 * Collapse a single variant to opacity-only: drop every transform key so the
 * element fades in place instead of translating/scaling. Non-object variants
 * (e.g. variant-label functions) are returned untouched.
 */
export function collapseVariant(variant: Variant): Variant {
  if (!isObjectVariant(variant)) return variant;
  const next: TargetAndTransition = {};
  for (const key of Object.keys(variant) as (keyof TargetAndTransition)[]) {
    if ((TRANSFORM_KEYS as readonly string[]).includes(key as string)) continue;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (next as any)[key] = (variant as any)[key];
  }
  return next;
}

/**
 * Collapse a whole `Variants` map (or a single variant) to opacity-only.
 * Pure — exported for unit testing without a DOM.
 */
export function collapseVariants(variants: Variants): Variants;
export function collapseVariants(variant: Variant): Variant;
export function collapseVariants(input: Variants | Variant): Variants | Variant {
  // Resolver functions / non-objects: nothing to collapse.
  if (typeof input !== "object" || input === null) {
    return input as Variant;
  }
  // A named-variants map → collapse each member.
  if (looksLikeVariantsMap(input)) {
    const out: Variants = {};
    for (const [name, variant] of Object.entries(input as Variants)) {
      out[name] = collapseVariant(variant);
    }
    return out;
  }
  // Otherwise a single TargetAndTransition variant.
  return collapseVariant(input as Variant);
}

/**
 * Reduced-motion-safe variant helper.
 *
 * Wraps motion's `useReducedMotion()`. Returns:
 * - `reduced`: whether the user prefers reduced motion (or `null` before hydration).
 * - `safe(variants)`: passes variants through untouched normally, but collapses
 *   them to opacity-only (no transform/translate) when reduced motion is on.
 */
export function useReducedMotionSafe() {
  const reduced = useReducedMotion();

  function safe(variants: Variants): Variants;
  function safe(variant: Variant): Variant;
  function safe(input: Variants | Variant): Variants | Variant {
    if (!reduced) return input;
    // Shape disambiguation (map vs single target) handled in collapseVariants.
    return collapseVariants(input as Variants) as Variants | Variant;
  }

  return { reduced: Boolean(reduced), safe } as const;
}
