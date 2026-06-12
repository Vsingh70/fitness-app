import type { ProgramDay } from "@/lib/programs/types";

export type ExMetaMap = Map<string, { name: string; primary_muscle?: string | null }>;

export const DOW = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

/** Up to three distinct primary muscles for a day, " · "-joined for summaries. */
export function exerciseSummary(day: ProgramDay, metaMap: ExMetaMap): string {
  const muscles = new Set<string>();
  for (const ex of day.exercises) {
    const m = metaMap.get(ex.exercise_id)?.primary_muscle;
    if (m) muscles.add(m.replace(/_/g, " "));
  }
  return Array.from(muscles).slice(0, 3).join(" · ");
}
