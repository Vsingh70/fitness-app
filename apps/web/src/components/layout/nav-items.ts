import {
  Activity,
  CalendarDays,
  Dumbbell,
  LineChart,
  ListChecks,
  UtensilsCrossed,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

export interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  mobileVisible: boolean;
  // Stable anchor for the onboarding spotlight tour. Emitted as `data-tutorial`
  // on both the desktop sidebar link and the mobile tab-bar link, so the tour
  // can highlight whichever is currently visible.
  tutorialId: string;
}

// Six destinations. Exercises folds into the Workouts hub and Body merges into
// Health, so neither is a nav destination. Settings lives off the primary bar
// (gear in the top bar). The mobile tab bar shows the five `mobileVisible` items.
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Today", icon: CalendarDays, mobileVisible: true, tutorialId: "nav-today" },
  {
    href: "/workouts",
    label: "Workouts",
    icon: Dumbbell,
    mobileVisible: true,
    tutorialId: "nav-workouts",
  },
  {
    href: "/programs",
    label: "Programs",
    icon: ListChecks,
    mobileVisible: true,
    tutorialId: "nav-programs",
  },
  {
    href: "/nutrition",
    label: "Nutrition",
    icon: UtensilsCrossed,
    mobileVisible: true,
    tutorialId: "nav-nutrition",
  },
  {
    // Desktop-only; mobile users reach Health via the Today steps/sleep tiles.
    href: "/health",
    label: "Health",
    icon: Activity,
    mobileVisible: false,
    tutorialId: "nav-health",
  },
  {
    href: "/analytics",
    label: "Insights",
    icon: LineChart,
    mobileVisible: true,
    tutorialId: "nav-insights",
  },
];
