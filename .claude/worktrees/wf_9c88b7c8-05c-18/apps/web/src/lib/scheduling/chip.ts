/**
 * Pure helpers for calendar chips: color by status, deload tint, shift body
 * shape for the reschedule mutation.
 */

import type { components } from "@/lib/api/types";

export type ScheduledWorkoutStatus = components["schemas"]["ScheduledWorkoutStatus"];

export function chipColor(status: ScheduledWorkoutStatus): string {
  switch (status) {
    case "planned":
      return "bg-accent/15 text-accent border-accent/30";
    case "in_progress":
      return "bg-warning/15 text-warning border-warning/30";
    case "completed":
      return "bg-success/15 text-success border-success/30";
    case "skipped":
      return "bg-surface text-text-tertiary border-border";
  }
}

export function deloadTint(isDeload: boolean): string {
  return isDeload ? "ring-2 ring-pr/40" : "";
}

export interface RescheduleBody {
  scheduled_for: string; // YYYY-MM-DD
}

export interface ReschedulePayload {
  scheduledId: string;
  body: RescheduleBody;
  shiftRemainingDays?: number;
}

/** Build the URL query suffix for a reschedule mutation. */
export function reschedulePathSuffix(shiftRemainingDays?: number): string {
  if (!shiftRemainingDays) return "";
  return `?shift_remaining_days=${shiftRemainingDays}`;
}

export function diffDays(from: string, to: string): number {
  const a = new Date(`${from}T12:00:00Z`).getTime();
  const b = new Date(`${to}T12:00:00Z`).getTime();
  return Math.round((b - a) / (24 * 60 * 60 * 1000));
}
