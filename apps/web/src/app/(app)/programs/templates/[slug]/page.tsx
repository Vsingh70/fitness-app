"use client";

import { useParams } from "next/navigation";

import { TemplateDetail } from "@/components/programs/template-detail";

export default function TemplateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  return <TemplateDetail slug={slug} />;
}
