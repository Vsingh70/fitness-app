"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import * as api from "@/lib/api/workouts";
import { useMe } from "@/lib/hooks/me";
import { isoDayInTz } from "@/lib/workouts/history";
import type { WorkoutSessionListItem } from "@/lib/workouts/types";

function startOfMonth(year: number, month: number): Date {
  return new Date(Date.UTC(year, month, 1, 12));
}

function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const date = new Date(Date.UTC(year, month + delta, 1));
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() };
}

function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
}

function monthLabel(year: number, month: number): string {
  return new Date(Date.UTC(year, month, 1)).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function CalendarPage() {
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";
  const today = new Date();
  const [cursor, setCursor] = useState<{ year: number; month: number }>({
    year: today.getFullYear(),
    month: today.getMonth(),
  });

  // Page through history; for the personal scale walking all pages is fine.
  const history = useInfiniteQuery({
    queryKey: ["workout-sessions", "infinite", { limit: 200 }],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => api.listSessions({ limit: 200, cursor: pageParam }),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    staleTime: 60_000,
  });

  // Auto-walk all pages so the calendar reflects everything we know about.
  if (history.hasNextPage && !history.isFetchingNextPage) {
    void history.fetchNextPage();
  }

  const items = useMemo<WorkoutSessionListItem[]>(
    () => history.data?.pages.flatMap((p) => p.items) ?? [],
    [history.data],
  );

  const byDay = useMemo(() => {
    const map = new Map<string, WorkoutSessionListItem[]>();
    for (const item of items) {
      const day = isoDayInTz(item.started_at, timezone);
      if (!map.has(day)) map.set(day, []);
      map.get(day)!.push(item);
    }
    return map;
  }, [items, timezone]);

  const firstOfMonth = startOfMonth(cursor.year, cursor.month);
  const leadingBlanks = (firstOfMonth.getUTCDay() + 6) % 7; // Monday=0
  const total = daysInMonth(cursor.year, cursor.month);
  const cells: ({ day: number; iso: string } | null)[] = [];
  for (let i = 0; i < leadingBlanks; i += 1) cells.push(null);
  for (let d = 1; d <= total; d += 1) {
    const iso = `${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ day: d, iso });
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold tracking-tight">Calendar</h1>
        <Link
          href="/workouts"
          className="hover:bg-surface border-border rounded-[var(--radius-button)] border px-3 py-1.5 text-sm"
        >
          List
        </Link>
      </header>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setCursor((c) => addMonths(c.year, c.month, -1))}
          aria-label="Previous month"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-lg font-medium">{monthLabel(cursor.year, cursor.month)}</h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setCursor((c) => addMonths(c.year, c.month, 1))}
          aria-label="Next month"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <Card>
        <CardContent>
          <div className="text-text-tertiary mb-2 grid grid-cols-7 gap-1 text-center text-xs uppercase">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((cell, idx) => {
              if (!cell) return <div key={`blank-${idx}`} />;
              const sessions = byDay.get(cell.iso) ?? [];
              const dotClass = sessions.length > 0 ? "bg-accent" : "bg-transparent";
              const content = (
                <div className="flex h-12 flex-col items-center justify-center">
                  <span className="text-sm">{cell.day}</span>
                  <span aria-hidden className={`mt-1 h-1.5 w-1.5 rounded-full ${dotClass}`} />
                </div>
              );
              if (sessions.length === 1) {
                return (
                  <Link
                    key={cell.iso}
                    href={`/workouts/${sessions[0]!.id}`}
                    className="hover:bg-surface rounded-md"
                    aria-label={`Open session on ${cell.iso}`}
                  >
                    {content}
                  </Link>
                );
              }
              if (sessions.length > 1) {
                return (
                  <details key={cell.iso} className="hover:bg-surface group rounded-md">
                    <summary className="cursor-pointer list-none">{content}</summary>
                    <div className="bg-surface-elevated border-border absolute mt-1 flex flex-col gap-1 rounded-md border p-2 text-xs shadow-md">
                      {sessions.map((s) => (
                        <Link key={s.id} href={`/workouts/${s.id}`} className="hover:text-accent">
                          {s.name ?? "Untitled session"}
                        </Link>
                      ))}
                    </div>
                  </details>
                );
              }
              return (
                <div
                  key={cell.iso}
                  className="text-text-tertiary flex h-12 flex-col items-center justify-center rounded-md"
                >
                  <span className="text-sm">{cell.day}</span>
                  <span aria-hidden className="mt-1 h-1.5 w-1.5 rounded-full bg-transparent" />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <p className="text-text-tertiary text-xs">Days shown in your timezone ({timezone}).</p>
    </div>
  );
}
