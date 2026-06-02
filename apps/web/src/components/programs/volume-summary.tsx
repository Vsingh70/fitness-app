"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { computeVolume, type VolumeEntry } from "@/lib/programs/volume";
import type { components } from "@/lib/api/types";

type Program = components["schemas"]["ProgramResponse"];
type Exercise = components["schemas"]["ExerciseResponse"];

interface VolumeSummaryProps {
  program: Program;
  exercises: Map<string, Exercise>;
}

const BAR_SCALE_MAX = 18;

export function VolumeSummary({ program, exercises }: VolumeSummaryProps) {
  const entries = computeVolume(program, exercises);
  return (
    <Card>
      <CardHeader>
        <span>Weekly volume</span>
        <span className="text-text-tertiary text-[11px] font-normal tracking-normal normal-case">
          Computed live · sets / muscle
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-0.5">
        {entries.length === 0 ? (
          <p className="text-text-secondary text-sm">Add exercises to see volume.</p>
        ) : (
          entries.map((entry) => <VolumeRow key={entry.muscle} entry={entry} />)
        )}
      </CardContent>
    </Card>
  );
}

function VolumeRow({ entry }: { entry: VolumeEntry }) {
  const widthPct = Math.min(100, (entry.sets / BAR_SCALE_MAX) * 100);
  const isWarn = entry.status !== "ok";
  return (
    <div className="grid grid-cols-[5rem_1fr_2.25rem] items-center gap-2 py-1.5 text-xs">
      <span className="text-text-secondary capitalize">{entry.muscle.replace(/_/g, " ")}</span>
      <div className="bg-surface h-1.5 overflow-hidden rounded-full">
        <div
          className={cn("h-full rounded-full", isWarn ? "bg-warning" : "bg-accent")}
          style={{ width: `${widthPct}%` }}
        />
      </div>
      <span
        className={cn(
          "text-right font-serif text-[11px] tabular-nums",
          isWarn ? "text-warning" : "text-text-tertiary",
        )}
      >
        {entry.sets}
      </span>
    </div>
  );
}
