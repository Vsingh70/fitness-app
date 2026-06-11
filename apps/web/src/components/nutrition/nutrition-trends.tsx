"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { TrendsBarChart, type TrendsBar } from "@/components/nutrition/trends-bar-chart";
import { UnderlineTabs } from "@/components/ui/tabs";
import type { MealResponse } from "@/lib/api/nutrition";
import { useMe } from "@/lib/hooks/me";
import { useMealsRange } from "@/lib/hooks/nutrition";
import { useNutritionTargets } from "@/lib/hooks/today";
import { isoDayInTz } from "@/lib/workouts/history";

type Range = "day" | "week" | "month";

const RANGE_TABS = [
  { value: "day" as const, label: "Day" },
  { value: "week" as const, label: "Week" },
  { value: "month" as const, label: "Month" },
] satisfies readonly { value: Range; label: string }[];

const RANGE_DAYS: Record<Range, number> = { day: 1, week: 7, month: 30 };

function n(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

/** Shift an ISO day (YYYY-MM-DD) by `delta` days, returning a new ISO day. */
function shiftIsoDay(isoDay: string, delta: number): string {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  return new Date(Date.UTC(y!, m! - 1, d! + delta)).toISOString().slice(0, 10);
}

/** ISO days (oldest → newest) ending today, in the user's timezone. */
function lastNDays(todayIso: string, count: number): string[] {
  const [y, m, d] = todayIso.split("-").map((s) => Number.parseInt(s, 10));
  const days: string[] = [];
  for (let i = count - 1; i >= 0; i--) {
    const dt = new Date(Date.UTC(y!, m! - 1, d! - i));
    days.push(dt.toISOString().slice(0, 10));
  }
  return days;
}

function totalsFromMeal(meal: MealResponse) {
  return meal.items.reduce(
    (acc, item) => ({ kcal: acc.kcal + n(item.kcal), p: acc.p + n(item.protein_g) }),
    { kcal: 0, p: 0 },
  );
}

function shortLabel(isoDay: string, timezone: string, range: Range): string {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const dt = new Date(Date.UTC(y!, m! - 1, d!, 12));
  if (range === "month") {
    return dt.toLocaleDateString(undefined, { timeZone: timezone, day: "numeric" });
  }
  return dt.toLocaleDateString(undefined, { timeZone: timezone, weekday: "narrow" });
}

/**
 * Client-side nutrition trends. There is no trends API endpoint, so the per-day
 * series is derived from the existing /v1/meals range (one fetch over the
 * window) and bucketed into local days. Targets come from /v1/nutrition/targets.
 */
export function NutritionTrends() {
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";
  const [range, setRange] = useState<Range>("week");

  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);
  const days = useMemo(() => lastNDays(today, RANGE_DAYS[range]), [today, range]);

  // One range fetch covering the whole window. The bounds are UTC midnights but
  // meals are bucketed by the user's local day; pad ±1 day so evening-local
  // meals at the oldest/newest day aren't dropped for non-UTC users. The extra
  // days fall outside `days` and are discarded by the per-day buckets below.
  const fromIso = useMemo(() => `${shiftIsoDay(days[0]!, -1)}T00:00:00.000Z`, [days]);
  const toIso = useMemo(() => `${shiftIsoDay(days[days.length - 1]!, 1)}T23:59:59.999Z`, [days]);
  const meals = useMealsRange(fromIso, toIso);
  const targets = useNutritionTargets();

  const kcalTarget = Math.round(n(targets.data?.target_kcal));

  // Bucket meals into local days.
  const perDay = useMemo(() => {
    const map = new Map<string, { kcal: number; p: number }>();
    for (const day of days) map.set(day, { kcal: 0, p: 0 });
    for (const meal of meals.data?.items ?? []) {
      const day = isoDayInTz(meal.eaten_at, timezone);
      const bucket = map.get(day);
      if (!bucket) continue;
      const t = totalsFromMeal(meal);
      bucket.kcal += t.kcal;
      bucket.p += t.p;
    }
    return map;
  }, [days, meals.data, timezone]);

  const bars: TrendsBar[] = useMemo(
    () =>
      days.map((day) => ({
        label: shortLabel(day, timezone, range),
        kcal: Math.round(perDay.get(day)?.kcal ?? 0),
        today: day === today,
      })),
    [days, perDay, timezone, range, today],
  );

  // Stat band — averaged over days that actually have any intake logged.
  const loggedDays = days.filter((day) => (perDay.get(day)?.kcal ?? 0) > 0);
  const avgKcal = loggedDays.length
    ? Math.round(
        loggedDays.reduce((s, day) => s + (perDay.get(day)?.kcal ?? 0), 0) / loggedDays.length,
      )
    : 0;
  const avgProtein = loggedDays.length
    ? Math.round(
        loggedDays.reduce((s, day) => s + (perDay.get(day)?.p ?? 0), 0) / loggedDays.length,
      )
    : 0;
  // On-target = within ±10% of the kcal target.
  const onTargetDays = kcalTarget
    ? loggedDays.filter((day) => {
        const kcal = perDay.get(day)?.kcal ?? 0;
        return Math.abs(kcal - kcalTarget) <= kcalTarget * 0.1;
      }).length
    : 0;
  const adherence = loggedDays.length ? Math.round((onTargetDays / loggedDays.length) * 100) : 0;

  const todayKcal = Math.round(perDay.get(today)?.kcal ?? 0);
  const todayProtein = Math.round(perDay.get(today)?.p ?? 0);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-7 pb-10">
      <header className="flex items-end justify-between gap-4">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
            Nutrition
          </span>
          <h1 className="text-text mt-1 font-serif text-[32px] font-medium tracking-tight">
            Trends
          </h1>
        </div>
        <nav
          aria-label="Day or week view"
          className="border-border flex gap-[18px] border-b text-[11px] font-semibold tracking-[0.08em] uppercase"
        >
          <Link
            href="/nutrition"
            className="text-text-secondary hover:text-text -mb-px border-b-[1.5px] border-transparent pb-[7px]"
          >
            Day
          </Link>
          <span className="border-text text-text -mb-px border-b-[1.5px] pb-[7px]">Week</span>
        </nav>
      </header>

      <UnderlineTabs tabs={RANGE_TABS} value={range} onChange={setRange} ariaLabel="Trend range" />

      {range === "day" ? (
        <div className="border-text flex flex-wrap items-baseline gap-x-[18px] gap-y-3 border-b-2 pb-3.5">
          <span className="text-text font-serif text-[52px] leading-[0.95] font-medium tracking-[-0.03em] tabular-nums">
            {todayKcal.toLocaleString()}
          </span>
          <span className="text-text-tertiary text-base">
            of {kcalTarget > 0 ? kcalTarget.toLocaleString() : "—"} kcal today
          </span>
          <span className="text-accent ml-auto font-serif text-[22px] font-medium tabular-nums">
            {todayProtein}
            <span className="text-text-tertiary text-[12px] font-normal">g protein</span>
          </span>
        </div>
      ) : meals.isLoading ? (
        <p className="text-text-secondary text-sm">Loading trends…</p>
      ) : meals.isError ? (
        <p className="text-destructive text-sm">Could not load trends.</p>
      ) : (
        <TrendsBarChart data={bars} target={kcalTarget} />
      )}

      <div className="grid grid-cols-2 gap-px sm:grid-cols-4">
        <Stat label="Avg / day" value={avgKcal.toLocaleString()} unit="kcal" />
        <Stat label="Avg protein" value={String(avgProtein)} unit="g" />
        <Stat
          label="Days on target"
          value={`${onTargetDays}/${loggedDays.length || RANGE_DAYS[range]}`}
        />
        <Stat label="Adherence" value={String(adherence)} unit="%" />
      </div>
    </div>
  );
}

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="border-text/80 flex flex-col gap-1 border-t pt-3">
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
        {label}
      </span>
      <span className="text-text font-serif text-[24px] font-medium tracking-tight tabular-nums">
        {value}
        {unit ? <span className="text-text-tertiary text-[12px] font-normal"> {unit}</span> : null}
      </span>
    </div>
  );
}
