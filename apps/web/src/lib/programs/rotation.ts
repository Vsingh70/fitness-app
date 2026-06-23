/**
 * Pure rotation projection. Timing is rotation, not calendar (01-program-model
 * §1): the calendar projects the active program's slots FORWARD from the current
 * position as an ordered upcoming sequence — no weekday-pinned cells.
 *
 * Walking the rotation: advance the slot index, wrap to 0 at microcycle end and
 * bump the repetition, and after the Nth repetition enter a deload microcycle
 * (when `auto_deload`) before rolling into the next mesocycle. The deload is one
 * pass over the same slots, marked separately and not counted in N.
 *
 * Unit-tested in tests/rotation.test.ts.
 */

import type { Program, ProgramDay, ProgramPosition } from "@/lib/programs/types";

export interface ProjectedSlot {
  /** Stable key for React; unique across the projected window. */
  key: string;
  slot: ProgramDay;
  /** 1-based ordinal within the projected window (1 = the current/today slot). */
  ordinal: number;
  /** True for the first item — the slot at the current rotation position. */
  isCurrent: boolean;
  isRest: boolean;
  /** This slot's microcycle repetition within the mesocycle (1..N), or null in deload. */
  repetition: number | null;
  /** True when this slot belongs to the appended deload microcycle. */
  isDeload: boolean;
}

/** One "Cycle N of M" (or "Deload") group of consecutive projected slots. */
export interface ProjectedCycle {
  key: string;
  /** Repetition number within the mesocycle, or null for the deload microcycle. */
  repetition: number | null;
  mesocycleLength: number;
  isDeload: boolean;
  slots: ProjectedSlot[];
}

/**
 * Project the rotation forward `count` slots from the program's current position.
 * Returns a flat ordered list; group it with {@link groupByCycle} for display.
 *
 * Rest-only programs (no training slots) yield an empty projection — there is no
 * meaningful rotation to advance.
 */
export function projectRotation(
  program: Program,
  position: ProgramPosition,
  count: number,
): ProjectedSlot[] {
  const slots = [...program.days].sort((a, b) => a.slot_index - b.slot_index);
  if (slots.length === 0 || count <= 0) return [];
  // A rotation with no training slots cannot advance; nothing to project.
  if (!slots.some((s) => !s.is_rest_day)) return [];

  const mesoLen = Math.max(1, position.mesocycle_length_microcycles);

  // Locate the starting slot by index; fall back to the first slot if the
  // position points outside the current slot list (e.g. after an edit).
  let idx = slots.findIndex((s) => s.slot_index === position.current_slot_index);
  if (idx < 0) idx = 0;
  let repetition = Math.min(Math.max(1, position.current_repetition), mesoLen);
  let inDeload = position.in_deload && program.auto_deload;

  const out: ProjectedSlot[] = [];
  for (let i = 0; i < count; i += 1) {
    const slot = slots[idx]!;
    out.push({
      key: `${repetition}-${inDeload ? "d" : "r"}-${i}-${slot.id}`,
      slot,
      ordinal: i + 1,
      isCurrent: i === 0,
      isRest: slot.is_rest_day,
      repetition: inDeload ? null : repetition,
      isDeload: inDeload,
    });

    // Advance the position for the next iteration.
    idx += 1;
    if (idx >= slots.length) {
      idx = 0;
      if (inDeload) {
        // Deload complete → roll into the next mesocycle.
        inDeload = false;
        repetition = 1;
      } else if (repetition >= mesoLen) {
        // Last repetition done → enter the deload microcycle, else next meso.
        if (program.auto_deload) {
          inDeload = true;
        } else {
          repetition = 1;
        }
      } else {
        repetition += 1;
      }
    }
  }
  return out;
}

/** Group a projection into consecutive "Cycle N" / "Deload" runs for display. */
export function groupByCycle(
  projected: ProjectedSlot[],
  mesocycleLength: number,
): ProjectedCycle[] {
  const mesoLen = Math.max(1, mesocycleLength);
  const cycles: ProjectedCycle[] = [];
  for (const item of projected) {
    const last = cycles[cycles.length - 1];
    if (!last || last.isDeload !== item.isDeload || last.repetition !== item.repetition) {
      cycles.push({
        key: `${item.isDeload ? "deload" : "cycle"}-${item.repetition ?? "d"}-${item.ordinal}`,
        repetition: item.repetition,
        mesocycleLength: mesoLen,
        isDeload: item.isDeload,
        slots: [item],
      });
    } else {
      last.slots.push(item);
    }
  }
  return cycles;
}
