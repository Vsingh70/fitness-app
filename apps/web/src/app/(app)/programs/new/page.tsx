import { ProgramsOnboarding } from "@/components/programs/onboarding";

/**
 * `/programs/new` is the single create entry point: it renders the two-card
 * chooser (Follow a template / Build your own) rather than silently spawning a
 * blank program. "Build your own" creates the blank draft and routes to the
 * builder; "Follow a template" routes to the gallery.
 */
export default function NewProgramPage() {
  return <ProgramsOnboarding />;
}
