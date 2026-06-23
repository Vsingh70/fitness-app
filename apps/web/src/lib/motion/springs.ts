/**
 * Shared spring transitions for `motion/react`.
 *
 * Restrained + physical: tuned for an editorial feel (<200ms perceived), not
 * decorative bounce. Use these instead of the CSS-duration tokens in
 * `tokens.css` (those remain for plain CSS transitions).
 */

/** ~150ms feel — taps, presses, small state changes. */
export const snappy = { type: "spring", stiffness: 460, damping: 38, mass: 0.9 } as const;

/** Gentle entrance / reveal motion. */
export const soft = { type: "spring", stiffness: 300, damping: 34 } as const;

/** Sheet / dialog enter-exit. */
export const sheet = { type: "spring", stiffness: 380, damping: 40 } as const;
