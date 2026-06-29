"use client";

import type { components } from "@/lib/api/types";
import { formatWeight } from "@/lib/utils/format-weight";

type PRRow = components["schemas"]["PRRowResponse"];
type ScatterPoint = components["schemas"]["ScatterPointResponse"];
type UnitSystem = components["schemas"]["UnitSystem"];

interface Props {
  recentPrs: PRRow[];
  setScatter: ScatterPoint[];
  unit?: UnitSystem;
}

function n(value: string | number): number {
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function PrTileRow({ recentPrs, setScatter, unit }: Props) {
  const bestE1rm = recentPrs.reduce<PRRow | null>((acc, pr) => {
    if (!acc) return pr;
    return n(pr.e1rm_kg) > n(acc.e1rm_kg) ? pr : acc;
  }, null);

  const bestWeight = setScatter.reduce<ScatterPoint | null>((acc, p) => {
    if (!acc) return p;
    return n(p.weight_kg) > n(acc.weight_kg) ? p : acc;
  }, null);

  const bestRepsAtTopWeight =
    bestWeight !== null
      ? setScatter
          .filter((p) => n(p.weight_kg) === n(bestWeight.weight_kg))
          .reduce((acc, p) => (p.reps > acc ? p.reps : acc), 0)
      : 0;

  const lastSeen = setScatter.length > 0 ? setScatter[setScatter.length - 1] : null;

  const [bestE1rmValue, bestE1rmUnit] = bestE1rm
    ? formatWeight(bestE1rm.e1rm_kg, unit).split(" ")
    : ["—", undefined];
  const [bestWeightValue, bestWeightUnit] = bestWeight
    ? formatWeight(bestWeight.weight_kg, unit).split(" ")
    : ["—", undefined];

  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
      <Tile
        label="Best e1RM"
        value={bestE1rmValue ?? "—"}
        unit={bestE1rmUnit}
        when={bestE1rm ? formatDate(bestE1rm.session_date) : undefined}
      />
      <Tile
        label="Heaviest"
        value={bestWeightValue ?? "—"}
        unit={bestWeightUnit}
        when={bestWeight ? formatDate(bestWeight.session_date) : undefined}
      />
      <Tile
        label="Top reps @ best"
        value={bestRepsAtTopWeight > 0 ? bestRepsAtTopWeight.toString() : "—"}
        unit={bestRepsAtTopWeight > 0 ? "reps" : undefined}
      />
      <Tile label="Last seen" value={lastSeen ? formatDate(lastSeen.session_date) : "—"} />
    </div>
  );
}

function Tile({
  label,
  value,
  unit,
  when,
}: {
  label: string;
  value: string;
  unit?: string;
  when?: string;
}) {
  return (
    <div className="border-border-strong flex flex-col gap-1.5 border-t pt-4">
      <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className="text-text font-serif text-[22px] font-medium tracking-tight tabular-nums">
          {value}
        </span>
        {unit ? <span className="text-text-secondary text-[13px] font-medium">{unit}</span> : null}
      </div>
      {when ? <span className="text-text-tertiary text-[11px]">{when}</span> : null}
    </div>
  );
}
