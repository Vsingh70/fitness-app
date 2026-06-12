import type { ReactNode } from "react";

// Editorial screen styles for every /programs/* route. Authored against the same
// design tokens the app already ships, so they load as-is. See programs.css.
import "./programs.css";

export default function ProgramsLayout({ children }: { children: ReactNode }) {
  return children;
}
