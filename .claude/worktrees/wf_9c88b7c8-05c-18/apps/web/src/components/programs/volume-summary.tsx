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

const TARGET_MIN = 8;
const TARGET_MAX = 22;
const BAR_SCALE_MAX = 28;

export function VolumeSummary({ program, exercises }: VolumeSummaryProps) {
  const entries = computeVolume(program, exercises);
  return (
    <Card>
      <CardHeader>
        <span>Weekly volume</span>
        <span className="text-text-tertiary text-[11px] font-normal normal-case tracking-normal">
          Primary 1.0 · secondary 0.5 · target {TARGET_MIN}–{TARGET_MAX}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
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
  const targetPct = (TARGET_MIN / BAR_SCALE_MAX) * 100;
  const isWarn = entry.status !== "ok";
  return (
    <div className="grid grid-cols-[8rem_1fr_2.5rem] items-center gap-3 text-sm">
      <span className="text-text-secondary text-xs capitalize">
        {entry.muscle.replace(/_/g, " ")}
      </span>
      <div className="bg-surface-sunken relative h-2 overflow-hidden rounded-full">
        <div
          className={cn(
            "h-full rounded-full",
            isWarn ? "bg-warning" : "bg-accent",
          )}
          style={{ width: `${widthPct}%` }}
        />
        <div
          className="bg-text-tertiary absolute top-0 h-full w-0.5"
          style={{ left: `${targetPct}%` }}
          aria-hidden
        />
      </div>
      <span
        className={cn(
          "font-serif text-right tabular-nums",
          isWarn ? "text-warning" : "text-text",
        )}
      >
        {entry.sets}
      </span>
    </div>
  );
}
