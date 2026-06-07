"use client";

import { MetricTrendCard } from "@/components/health/metric-trend-card";
import { StatTile } from "@/components/ui/stat-tile";
import { useReadinessHistory } from "@/lib/hooks/readiness";
import {
  formatHr,
  formatHrv,
  formatSleep,
  formatSteps,
  sleepHours,
} from "@/lib/utils/format-health";
import { toNum } from "@/lib/utils/format-weight";

export default function HealthPage() {
  const history = useReadinessHistory(30);
  const items = history.data?.items;

  // newest-first view for "latest" stat tiles
  const rows = (items ?? [])
    .slice()
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

  const latestSteps = rows.find((r) => (r.steps ?? null) !== null)?.steps ?? null;
  const latestSleep = rows.find((r) => (r.sleep_minutes ?? null) !== null)?.sleep_minutes ?? null;
  const latestHr = rows.find((r) => (r.resting_hr ?? null) !== null)?.resting_hr ?? null;
  const latestHrv = toNum(rows.find((r) => toNum(r.hrv_ms) !== null)?.hrv_ms);

  const loading = history.isLoading;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <header>
        <h1 className="font-serif text-[32px] font-medium tracking-tight">Health</h1>
        <p className="text-text-secondary mt-1 text-sm">
          Daily steps, sleep, and recovery metrics synced from your watch.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Steps" value={loading ? "—" : formatSteps(latestSteps)} />
        <StatTile label="Last sleep" value={loading ? "—" : formatSleep(latestSleep)} />
        <StatTile label="Resting HR" value={loading ? "—" : formatHr(latestHr)} />
        <StatTile label="HRV" value={loading ? "—" : formatHrv(latestHrv)} />
      </div>

      <MetricTrendCard
        title="Steps"
        primaryLabel="Steps"
        items={items}
        mapValue={(d) => d.steps ?? null}
        isLoading={history.isLoading}
        isError={history.isError}
      />
      <MetricTrendCard
        title="Sleep"
        unit="h"
        primaryLabel="Sleep"
        items={items}
        mapValue={(d) => sleepHours(d.sleep_minutes)}
        isLoading={history.isLoading}
        isError={history.isError}
      />
      <MetricTrendCard
        title="Resting HR"
        unit="bpm"
        primaryLabel="Resting HR"
        items={items}
        mapValue={(d) => d.resting_hr ?? null}
        isLoading={history.isLoading}
        isError={history.isError}
      />
      <MetricTrendCard
        title="HRV"
        unit="ms"
        primaryLabel="HRV"
        items={items}
        mapValue={(d) => toNum(d.hrv_ms)}
        isLoading={history.isLoading}
        isError={history.isError}
      />
    </div>
  );
}
