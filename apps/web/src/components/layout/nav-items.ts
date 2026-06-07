import {
  CalendarDays,
  Dumbbell,
  LibraryBig,
  LineChart,
  ListChecks,
  Scale,
  Settings,
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
    // Desktop-only in the sidebar to keep the mobile tab bar at 5; mobile users
    // reach the library from the Workouts screen + the in-workout exercise picker.
    href: "/exercises",
    label: "Exercises",
    icon: LibraryBig,
    mobileVisible: false,
    tutorialId: "nav-exercises",
  },
  {
    href: "/nutrition",
    label: "Nutrition",
    icon: UtensilsCrossed,
    mobileVisible: true,
    tutorialId: "nav-nutrition",
  },
  {
    href: "/analytics",
    label: "Insights",
    icon: LineChart,
    mobileVisible: true,
    tutorialId: "nav-insights",
  },
  {
    // Desktop-only; mobile users reach Body via the Today weight tile.
    href: "/body",
    label: "Body",
    icon: Scale,
    mobileVisible: false,
    tutorialId: "nav-body",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
    mobileVisible: false,
    tutorialId: "nav-settings",
  },
];
