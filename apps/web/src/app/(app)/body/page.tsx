"use client";

import { useState } from "react";

import { LogWeightSheet } from "@/components/body/log-weight-sheet";
import { WeightHistoryList } from "@/components/body/weight-history-list";
import { WeightTrendCard } from "@/components/body/weight-trend-card";
import { Button } from "@/components/ui/button";
import { StatTile } from "@/components/ui/stat-tile";
import { useBodyMetrics, useBodyTrend } from "@/lib/hooks/body-metrics";
import { useMe } from "@/lib/hooks/me";
import {
  kgToDisplay,
  relativeDate,
  toNum,
  weeklyDelta,
  weightUnitLabel,
} from "@/lib/utils/format-weight";

export default function BodyPage() {
  const me = useMe();
  const unit = me.data?.unit_system;
  const list = useBodyMetrics();
  const trend = useBodyTrend();
  const [sheetOpen, setSheetOpen] = useState(false);

  const items = list.data?.items;
  const latest = items?.find((r) => toNum(r.weight_kg) !== null) ?? null;
  const delta = weeklyDelta(items, unit);
  const deltaDir = delta
    ? delta.kgDelta > 0
      ? "up"
      : delta.kgDelta < 0
        ? "down"
        : "flat"
    : undefined;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <header>
        <h1 className="font-serif text-[32px] font-medium tracking-tight">Body</h1>
        <p className="text-text-secondary mt-1 text-sm">
          Track body weight and composition over time.
        </p>
      </header>

      <div className="flex justify-end">
        <Button size="sm" onClick={() => setSheetOpen(true)}>
          Log weight
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <StatTile
          label="Current weight"
          value={list.isLoading ? "—" : latest ? kgToDisplay(latest.weight_kg, unit) : "—"}
          unit={latest ? weightUnitLabel(unit) : undefined}
        />
        <StatTile
          label="Weekly change"
          value={
            list.isLoading
              ? "—"
              : delta
                ? `${delta.displayDelta >= 0 ? "+" : "−"}${Math.abs(delta.displayDelta)}`
                : "—"
          }
          unit={delta ? weightUnitLabel(unit) : undefined}
          trend={deltaDir}
          delta={delta ? "vs last week" : undefined}
        />
        <StatTile
          label="Last logged"
          value={list.isLoading ? "—" : latest ? relativeDate(latest.recorded_at) : "—"}
        />
      </div>

      <WeightTrendCard
        data={trend.data}
        isLoading={trend.isLoading}
        isError={trend.isError}
        unit={unit}
      />

      <WeightHistoryList
        items={items}
        isLoading={list.isLoading}
        isError={list.isError}
        unit={unit}
      />

      <LogWeightSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
    </div>
  );
}
