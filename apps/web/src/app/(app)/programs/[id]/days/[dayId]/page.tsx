"use client";

import { useParams } from "next/navigation";

import { PerDayDetail } from "@/components/programs/per-day-detail";

export default function ProgramDayPage() {
  const { id, dayId } = useParams<{ id: string; dayId: string }>();
  return <PerDayDetail programId={id} dayId={dayId} />;
}
