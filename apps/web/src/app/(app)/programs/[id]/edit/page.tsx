"use client";

import { useParams } from "next/navigation";

import { ProgramBuilder } from "@/components/programs/program-builder";

export default function ProgramEditPage() {
  const { id } = useParams<{ id: string }>();
  return <ProgramBuilder programId={id} />;
}
