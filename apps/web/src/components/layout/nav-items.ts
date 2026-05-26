import {
  CalendarDays,
  Dumbbell,
  LineChart,
  ListChecks,
  Settings,
  UtensilsCrossed,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

export interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  mobileVisible: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Today", icon: CalendarDays, mobileVisible: true },
  { href: "/workouts", label: "Workouts", icon: Dumbbell, mobileVisible: true },
  { href: "/programs", label: "Programs", icon: ListChecks, mobileVisible: true },
  { href: "/nutrition", label: "Nutrition", icon: UtensilsCrossed, mobileVisible: true },
  { href: "/analytics", label: "Insights", icon: LineChart, mobileVisible: true },
  { href: "/settings", label: "Settings", icon: Settings, mobileVisible: false },
];
