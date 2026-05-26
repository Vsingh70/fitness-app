import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { cn } from "@/lib/cn";

type Trend = "up" | "down" | "flat";

interface StatTileProps {
  label: string;
  value: ReactNode;
  unit?: string;
  trend?: Trend;
  delta?: string;
  className?: string;
}

const TREND_ICON = { up: ArrowUp, down: ArrowDown, flat: Minus };
const TREND_COLOR: Record<Trend, string> = {
  up: "text-success",
  down: "text-destructive",
  flat: "text-text-tertiary",
};

export function StatTile({ label, value, unit, trend, delta, className }: StatTileProps) {
  const TrendIcon = trend ? TREND_ICON[trend] : null;
  return (
    <div
      className={cn(
        "border-border bg-surface-elevated flex flex-col gap-1 rounded-[var(--radius-card)] border p-4",
        className,
      )}
    >
      <span className="text-text-secondary text-sm">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-text text-3xl font-semibold tabular-nums">{value}</span>
        {unit ? <span className="text-text-secondary text-sm">{unit}</span> : null}
      </div>
      {trend && delta ? (
        <div className={cn("flex items-center gap-1 text-xs", TREND_COLOR[trend])}>
          {TrendIcon ? <TrendIcon className="h-3 w-3" /> : null}
          <span>{delta}</span>
        </div>
      ) : null}
    </div>
  );
}
