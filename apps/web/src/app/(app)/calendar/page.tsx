"use client";

import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { useInfiniteQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet } from "@/components/ui/sheet";
import * as workoutsApi from "@/lib/api/workouts";
import { useMe } from "@/lib/hooks/me";
import {
  useScheduledWorkouts,
  useStartScheduled,
  useUpdateScheduled,
} from "@/lib/hooks/scheduling";
import { chipColor, deloadTint, diffDays } from "@/lib/scheduling/chip";
import { isoDayInTz } from "@/lib/workouts/history";
import type { components } from "@/lib/api/types";

type Scheduled = components["schemas"]["ScheduledWorkoutWithDay"];
type WorkoutSessionListItem = components["schemas"]["WorkoutSessionListItem"];

function startOfMonth(year: number, month: number): Date {
  return new Date(Date.UTC(year, month, 1, 12));
}
function addMonths(y: number, m: number, delta: number): { year: number; month: number } {
  const d = new Date(Date.UTC(y, m + delta, 1));
  return { year: d.getUTCFullYear(), month: d.getUTCMonth() };
}
function daysIn(y: number, m: number): number {
  return new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
}
function monthLabel(y: number, m: number): string {
  return new Date(Date.UTC(y, m, 1)).toLocaleDateString(undefined, {
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
  const [openDetail, setOpenDetail] = useState<Scheduled | null>(null);
  const [shiftHeld, setShiftHeld] = useState(false);

  const monthStart = `${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-01`;
  const monthEnd = `${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(daysIn(cursor.year, cursor.month)).padStart(2, "0")}`;

  const scheduled = useScheduledWorkouts({ from: monthStart, to: monthEnd });
  const update = useUpdateScheduled();
  const start = useStartScheduled();
  const router = useRouter();

  // Past completed sessions sourced from /v1/workout-sessions.
  const sessions = useInfiniteQuery({
    queryKey: ["workout-sessions", "infinite", { limit: 200 }],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => workoutsApi.listSessions({ limit: 200, cursor: pageParam }),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    staleTime: 60_000,
  });
  if (sessions.hasNextPage && !sessions.isFetchingNextPage) {
    void sessions.fetchNextPage();
  }
  const sessionItems = useMemo<WorkoutSessionListItem[]>(
    () => sessions.data?.pages.flatMap((p) => p.items) ?? [],
    [sessions.data],
  );

  const scheduledByDay = useMemo(() => {
    const map = new Map<string, Scheduled[]>();
    for (const item of scheduled.data?.items ?? []) {
      const day = item.scheduled_for;
      if (!map.has(day)) map.set(day, []);
      map.get(day)!.push(item);
    }
    return map;
  }, [scheduled.data]);

  const sessionsByDay = useMemo(() => {
    const map = new Map<string, WorkoutSessionListItem[]>();
    for (const session of sessionItems) {
      const day = isoDayInTz(session.started_at, timezone);
      if (!map.has(day)) map.set(day, []);
      map.get(day)!.push(session);
    }
    return map;
  }, [sessionItems, timezone]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const onDragEnd = (event: DragEndEvent) => {
    const id = event.active.id as string;
    const overId = event.over?.id;
    if (!overId || typeof overId !== "string") return;
    const item = (scheduled.data?.items ?? []).find((i) => i.id === id);
    if (!item || item.scheduled_for === overId) return;
    if (item.status !== "planned") return;
    const delta = diffDays(item.scheduled_for, overId);
    update.mutate({
      id,
      body: { scheduled_for: overId },
      shiftRemainingDays: shiftHeld ? delta : 0,
    });
  };

  const leadingBlanks = (startOfMonth(cursor.year, cursor.month).getUTCDay() + 6) % 7;
  const total = daysIn(cursor.year, cursor.month);
  const cells: ({ day: number; iso: string } | null)[] = [];
  for (let i = 0; i < leadingBlanks; i += 1) cells.push(null);
  for (let d = 1; d <= total; d += 1) {
    const iso = `${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ day: d, iso });
  }

  return (
    <div
      className="mx-auto flex max-w-4xl flex-col gap-4"
      onKeyDown={(e) => {
        if (e.key === "Shift") setShiftHeld(true);
      }}
      onKeyUp={(e) => {
        if (e.key === "Shift") setShiftHeld(false);
      }}
    >
      <header className="flex items-center justify-between">
        <h1 className="font-serif text-[32px] font-medium tracking-tight">Calendar</h1>
        <Link
          href="/workouts"
          className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold uppercase tracking-[0.08em]"
        >
          List view
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
        <h2 className="font-serif text-xl font-medium tracking-tight">
          {monthLabel(cursor.year, cursor.month)}
        </h2>
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

      <p className="text-text-tertiary text-xs">
        Drag a planned chip to a different day to reschedule. Hold Shift while dragging to also
        shift every later workout in the same program by the same delta.
      </p>

      <Card>
        <CardContent>
          <DndContext sensors={sensors} onDragEnd={onDragEnd}>
            <div className="text-text-tertiary mb-2 grid grid-cols-7 gap-1 text-center text-xs uppercase">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
                <span key={d}>{d}</span>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {cells.map((cell, idx) =>
                cell ? (
                  <DayCell
                    key={cell.iso}
                    iso={cell.iso}
                    day={cell.day}
                    scheduled={scheduledByDay.get(cell.iso) ?? []}
                    sessions={sessionsByDay.get(cell.iso) ?? []}
                    onChipClick={(s) => setOpenDetail(s)}
                  />
                ) : (
                  <div key={`blank-${idx}`} className="h-24" />
                ),
              )}
            </div>
          </DndContext>
        </CardContent>
      </Card>

      <p className="text-text-tertiary text-xs">
        Days shown in your timezone ({timezone}).{" "}
        {shiftHeld ? <span className="text-accent">Shift held: cascade is on.</span> : null}
      </p>

      <Sheet
        open={openDetail !== null}
        onOpenChange={(o) => !o && setOpenDetail(null)}
        title="Scheduled workout"
      >
        {openDetail ? (
          <div className="flex flex-col gap-3 text-sm">
            <div>
              <span className="text-text-tertiary text-xs">Program</span>
              <p>{openDetail.program_name ?? "-"}</p>
            </div>
            <div>
              <span className="text-text-tertiary text-xs">Day</span>
              <p>{openDetail.program_day_name ?? "-"}</p>
            </div>
            <div>
              <span className="text-text-tertiary text-xs">Date</span>
              <p>{openDetail.scheduled_for}</p>
            </div>
            <div>
              <span className="text-text-tertiary text-xs">Status</span>
              <p>{openDetail.status}</p>
            </div>
            <div className="flex gap-2 pt-2">
              {openDetail.status === "planned" || openDetail.status === "in_progress" ? (
                <Button
                  type="button"
                  onClick={() =>
                    start.mutate(openDetail.id, {
                      onSuccess: (session) => {
                        setOpenDetail(null);
                        router.push(`/workouts/${session.id}`);
                      },
                    })
                  }
                  disabled={start.isPending}
                >
                  {start.isPending ? "Starting..." : "Start"}
                </Button>
              ) : null}
              {openDetail.status === "planned" ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    update.mutate(
                      { id: openDetail.id, body: { status: "skipped" } },
                      { onSuccess: () => setOpenDetail(null) },
                    )
                  }
                >
                  Skip
                </Button>
              ) : null}
              {openDetail.status === "skipped" ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    update.mutate(
                      { id: openDetail.id, body: { status: "planned" } },
                      { onSuccess: () => setOpenDetail(null) },
                    )
                  }
                >
                  Unskip
                </Button>
              ) : null}
            </div>
          </div>
        ) : null}
      </Sheet>
    </div>
  );
}

function DayCell({
  iso,
  day,
  scheduled,
  sessions,
  onChipClick,
}: {
  iso: string;
  day: number;
  scheduled: Scheduled[];
  sessions: WorkoutSessionListItem[];
  onChipClick: (s: Scheduled) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: iso });
  return (
    <div
      ref={setNodeRef}
      className={`flex h-24 flex-col gap-1 rounded-[var(--radius-card)] border p-1 text-xs ${
        isOver ? "border-accent bg-accent-soft" : "border-border"
      }`}
    >
      <span className="text-text-tertiary">{day}</span>
      <div className="flex flex-1 flex-col gap-1 overflow-hidden">
        {scheduled.map((s) => (
          <ScheduledChip key={s.id} item={s} onClick={() => onChipClick(s)} />
        ))}
        {sessions.map((s) => (
          <span
            key={s.id}
            className="bg-success-soft text-success border-success/40 truncate rounded border px-1 py-0.5"
          >
            {s.name ?? "Session"}
          </span>
        ))}
      </div>
    </div>
  );
}

function ScheduledChip({ item, onClick }: { item: Scheduled; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: item.id,
    disabled: item.status !== "planned",
  });
  return (
    <button
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      type="button"
      onClick={onClick}
      className={`truncate rounded border px-1 py-0.5 text-left ${chipColor(item.status)} ${deloadTint(
        item.is_deload,
      )} ${isDragging ? "opacity-50" : ""}`}
    >
      {item.program_day_name ?? "Workout"}
    </button>
  );
}
