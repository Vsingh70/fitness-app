"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { TrendChart, type TrendPoint } from "@/components/charts/trend-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import * as api from "@/lib/api/workouts";
import { useMe } from "@/lib/hooks/me";
import {
  allSetsForExercise,
  bestE1RMByDay,
  filterSessionsByRange,
  rangeStartMs,
  volumeByDay,
  type RangeKey,
} from "@/lib/workouts/history";
import type { WorkoutSession } from "@/lib/workouts/types";

const RANGE_LABELS: Record<RangeKey, string> = {
  "4w": "4w",
  "12w": "12w",
  "6mo": "6mo",
  "1y": "1y",
  all: "All",
};

function useAllSessionsDetail() {
  // Walk the cursor-paginated list, then fetch each session's full detail.
  // This is the client-side aggregation flagged in clarifying Qs as fine for
  // personal scale; a server-side history endpoint is the long-term home.
  const list = useInfiniteQuery({
    queryKey: ["workout-sessions", "detail-aggregation"],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => api.listSessions({ limit: 200, cursor: pageParam }),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (list.hasNextPage && !list.isFetchingNextPage) void list.fetchNextPage();
  }, [list, list.hasNextPage, list.isFetchingNextPage]);

  const ids = useMemo(
    () => list.data?.pages.flatMap((p) => p.items.map((i) => i.id)) ?? [],
    [list.data],
  );

  const details = useQuery({
    queryKey: ["session-details", ids.join(",")],
    queryFn: async () => {
      if (ids.length === 0) return [] as WorkoutSession[];
      const out: WorkoutSession[] = [];
      for (const id of ids) {
        try {
          out.push(await api.getSession(id));
        } catch {
          // Skip sessions we can't load.
        }
      }
      return out;
    },
    enabled: ids.length > 0 && !list.hasNextPage,
    staleTime: 60_000,
  });

  return {
    isLoading: list.isLoading || details.isLoading || list.isFetchingNextPage,
    isError: list.isError || details.isError,
    sessions: details.data ?? [],
  };
}

export default function ExerciseHistoryPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";
  const all = useAllSessionsDetail();

  const [range, setRange] = useState<RangeKey>("12w");
  const [compareId, setCompareId] = useState<string | null>(null);
  const [tablePage, setTablePage] = useState(0);
  const ROWS_PER_PAGE = 25;

  const exerciseQuery = useQuery({
    queryKey: ["exercise-meta-single", id],
    queryFn: async () => {
      const list = await api.searchExercises(undefined, { limit: 200 });
      return list.items.find((ex) => ex.id === id) ?? null;
    },
    staleTime: 5 * 60_000,
  });

  const allExercises = useQuery({
    queryKey: ["exercises-all-for-compare"],
    queryFn: () => api.searchExercises(undefined, { limit: 200 }),
    staleTime: 5 * 60_000,
  });

  const filteredSessions = useMemo(
    () => filterSessionsByRange(all.sessions, range),
    [all.sessions, range],
  );

  const e1rmPrimary = useMemo(
    () => bestE1RMByDay(filteredSessions, id, timezone),
    [filteredSessions, id, timezone],
  );
  const volumePrimary = useMemo(
    () => volumeByDay(filteredSessions, id, timezone),
    [filteredSessions, id, timezone],
  );
  const e1rmOverlay = useMemo(
    () => (compareId ? bestE1RMByDay(filteredSessions, compareId, timezone) : []),
    [filteredSessions, compareId, timezone],
  );

  const e1rmMerged = useMemo<TrendPoint[]>(() => {
    if (!compareId) return e1rmPrimary;
    const byDate = new Map<string, TrendPoint>();
    for (const p of e1rmPrimary) byDate.set(p.date, { date: p.date, value: p.value });
    for (const p of e1rmOverlay) {
      const prev = byDate.get(p.date);
      if (prev) prev.overlay = p.value;
      else byDate.set(p.date, { date: p.date, value: 0, overlay: p.value });
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  }, [e1rmPrimary, e1rmOverlay, compareId]);

  const allSets = useMemo(
    () => allSetsForExercise(filteredSessions, id, timezone),
    [filteredSessions, id, timezone],
  );
  const pagedSets = allSets.slice(tablePage * ROWS_PER_PAGE, (tablePage + 1) * ROWS_PER_PAGE);
  const totalPages = Math.max(1, Math.ceil(allSets.length / ROWS_PER_PAGE));

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <header>
        <Link href="/workouts" className="text-text-tertiary text-xs hover:underline">
          ← Back to workouts
        </Link>
        <h1 className="font-serif mt-1 text-[32px] font-medium tracking-tight">
          {exerciseQuery.data?.name ?? "Exercise"}
        </h1>
        <p className="text-text-secondary text-sm">
          {exerciseQuery.data?.primary_muscle} - {exerciseQuery.data?.equipment}
        </p>
      </header>

      <div className="flex items-center gap-2" role="tablist" aria-label="Range filter">
        {(Object.keys(RANGE_LABELS) as RangeKey[]).map((key) => (
          <Button
            key={key}
            type="button"
            size="sm"
            variant={range === key ? "primary" : "secondary"}
            onClick={() => setRange(key)}
            data-testid={`range-${key}`}
            aria-pressed={range === key}
          >
            {RANGE_LABELS[key]}
          </Button>
        ))}
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Estimated 1RM</h2>
            <p className="text-text-tertiary text-xs">
              {rangeStartMs(range) === null
                ? "All time"
                : `Since ${new Date(rangeStartMs(range)!).toLocaleDateString()}`}
            </p>
          </div>
          <select
            className="bg-surface text-text border-border h-8 rounded-[var(--radius-button)] border px-2 text-sm"
            value={compareId ?? ""}
            onChange={(e) => setCompareId(e.target.value || null)}
            aria-label="Compare exercise"
          >
            <option value="">Compare with...</option>
            {allExercises.data?.items
              .filter((ex) => ex.id !== id)
              .map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name}
                </option>
              ))}
          </select>
        </CardHeader>
        <CardContent>
          <TrendChart
            kind="line"
            data={e1rmMerged}
            unit="kg"
            primaryLabel={exerciseQuery.data?.name ?? "e1RM"}
            overlayLabel={
              compareId
                ? allExercises.data?.items.find((ex) => ex.id === compareId)?.name
                : undefined
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Volume per session</h2>
        </CardHeader>
        <CardContent>
          <TrendChart kind="bar" data={volumePrimary} unit="kg" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">All sets</h2>
          <p className="text-text-tertiary text-xs">
            {allSets.length} set{allSets.length === 1 ? "" : "s"} in the selected range.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {all.isLoading ? (
            <p className="text-text-secondary text-sm">Loading...</p>
          ) : all.isError ? (
            <p className="text-destructive text-sm">Could not load history.</p>
          ) : pagedSets.length === 0 ? (
            <p className="text-text-secondary text-sm">No sets in this range.</p>
          ) : (
            <table className="w-full text-sm tabular-nums">
              <thead className="text-text-tertiary text-left text-xs uppercase">
                <tr>
                  <th className="py-1">Date</th>
                  <th>Weight</th>
                  <th>Reps</th>
                  <th>RPE</th>
                </tr>
              </thead>
              <tbody>
                {pagedSets.map(({ setId, sessionDate, set }) => (
                  <tr key={setId} className="border-border border-t">
                    <td className="py-1">{sessionDate}</td>
                    <td>{set.weight_kg ?? "-"}</td>
                    <td>{set.reps ?? "-"}</td>
                    <td>{set.rpe ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {totalPages > 1 ? (
            <div className="mt-2 flex items-center justify-between text-xs">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={tablePage === 0}
                onClick={() => setTablePage((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              <span className="text-text-tertiary">
                Page {tablePage + 1} of {totalPages}
              </span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={tablePage + 1 >= totalPages}
                onClick={() => setTablePage((p) => Math.min(totalPages - 1, p + 1))}
              >
                Next
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <p className="text-text-tertiary text-xs">
        History is computed client-side today; a dedicated /v1/exercises/{"{id}"}/history endpoint
        lands with the analytics phase.
      </p>
    </div>
  );
}
