"use client";

import { useMemo, useState } from "react";

import { LogWeightSheet } from "@/components/body/log-weight-sheet";
import { WeightHistoryList } from "@/components/body/weight-history-list";
import { WeightTrendCard } from "@/components/body/weight-trend-card";
import { MetricTrendCard } from "@/components/health/metric-trend-card";
import { WearableConnectionCard } from "@/components/health/wearable-connection-card";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatTile } from "@/components/ui/stat-tile";
import { useBodyMetrics, useBodyTrend } from "@/lib/hooks/body-metrics";
import { useMe } from "@/lib/hooks/me";
import { useReadinessHistory } from "@/lib/hooks/readiness";
import {
  formatHr,
  formatHrv,
  formatSleep,
  formatSteps,
  sleepHours,
} from "@/lib/utils/format-health";
import {
  kgToDisplay,
  relativeDate,
  toNum,
  weeklyDelta,
  weightUnitLabel,
} from "@/lib/utils/format-weight";

/**
 * Health — the merged Body + Health surface (`03-information-architecture.md`).
 * Two labeled sections: Metrics (manual weight + composition, formerly Body) and
 * Wearable (synced steps / sleep / recovery + the one connection). Each section
 * staggers in on load via RevealGroup; reduced motion fades only.
 */
export default function HealthPage() {
  const me = useMe();
  const unit = me.data?.unit_system;

  // Metrics (formerly Body)
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

  // Wearable (formerly Health)
  const history = useReadinessHistory(30);
  const readiness = history.data?.items;

  // newest-first view for "latest" stat tiles
  const rows = useMemo(
    () => (readiness ?? []).toSorted((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)),
    [readiness],
  );

  const latestSteps = rows.find((r) => (r.steps ?? null) !== null)?.steps ?? null;
  const latestSleep = rows.find((r) => (r.sleep_minutes ?? null) !== null)?.sleep_minutes ?? null;
  const latestHr = rows.find((r) => (r.resting_hr ?? null) !== null)?.resting_hr ?? null;
  const latestHrv = toNum(rows.find((r) => toNum(r.hrv_ms) !== null)?.hrv_ms);

  const wearableLoading = history.isLoading;

  return (
    <RevealGroup className="page-shell flex flex-col" style={{ gap: "var(--space-section)" }}>
      <RevealItem>
        <header>
          <h1
            className="font-serif font-medium tracking-tight"
            style={{ fontSize: "var(--text-h2)" }}
          >
            Health
          </h1>
          <p className="text-text-secondary mt-1.5 text-sm">
            Body metrics you log and the wearable data synced from your watch.
          </p>
        </header>
      </RevealItem>

      {/* Metrics (formerly Body) — manual weight + composition. */}
      <RevealItem>
        <section className="flex flex-col gap-4" aria-labelledby="metrics-heading">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2
                id="metrics-heading"
                className="text-text-secondary text-xs font-semibold tracking-[0.12em] uppercase"
              >
                Metrics
              </h2>
              <p className="text-text-tertiary mt-1 text-sm">
                Body weight and composition over time.
              </p>
            </div>
            <Button size="sm" onClick={() => setSheetOpen(true)}>
              Log weight
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
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

          <Card>
            <CardHeader>Weight history</CardHeader>
            <CardContent>
              <WeightHistoryList
                items={items}
                isLoading={list.isLoading}
                isError={list.isError}
                unit={unit}
              />
            </CardContent>
          </Card>
        </section>
      </RevealItem>

      {/* Wearable (formerly Health) — synced steps / sleep / recovery. */}
      <RevealItem>
        <section className="flex flex-col gap-4" aria-labelledby="wearable-heading">
          <div>
            <h2
              id="wearable-heading"
              className="text-text-secondary text-xs font-semibold tracking-[0.12em] uppercase"
            >
              Wearable
            </h2>
            <p className="text-text-tertiary mt-1 text-sm">
              Daily steps, sleep, and recovery metrics synced from your watch.
            </p>
          </div>

          <WearableConnectionCard />

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Steps" value={wearableLoading ? "—" : formatSteps(latestSteps)} />
            <StatTile label="Last sleep" value={wearableLoading ? "—" : formatSleep(latestSleep)} />
            <StatTile label="Resting HR" value={wearableLoading ? "—" : formatHr(latestHr)} />
            <StatTile label="HRV" value={wearableLoading ? "—" : formatHrv(latestHrv)} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <MetricTrendCard
              title="Steps"
              primaryLabel="Steps"
              items={readiness}
              mapValue={(d) => d.steps ?? null}
              isLoading={history.isLoading}
              isError={history.isError}
            />
            <MetricTrendCard
              title="Sleep"
              unit="h"
              primaryLabel="Sleep"
              items={readiness}
              mapValue={(d) => sleepHours(d.sleep_minutes)}
              isLoading={history.isLoading}
              isError={history.isError}
            />
            <MetricTrendCard
              title="Resting HR"
              unit="bpm"
              primaryLabel="Resting HR"
              items={readiness}
              mapValue={(d) => d.resting_hr ?? null}
              isLoading={history.isLoading}
              isError={history.isError}
            />
            <MetricTrendCard
              title="HRV"
              unit="ms"
              primaryLabel="HRV"
              items={readiness}
              mapValue={(d) => toNum(d.hrv_ms)}
              isLoading={history.isLoading}
              isError={history.isError}
            />
          </div>
        </section>
      </RevealItem>

      <LogWeightSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
    </RevealGroup>
  );
}
