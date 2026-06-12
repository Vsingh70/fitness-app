"use client";

import { useParams } from "next/navigation";

import { ProgramOverview } from "@/components/programs/program-overview";

export default function ProgramViewPage() {
  const { id } = useParams<{ id: string }>();
  return <ProgramOverview programId={id} />;
}
