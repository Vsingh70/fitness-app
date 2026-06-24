import { ExerciseDetailView } from "./exercise-detail-view";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ExerciseDetailView id={id} />;
}
