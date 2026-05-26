"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/cn";

export function DesktopSidebar() {
  const pathname = usePathname();
  return (
    <aside className="border-border bg-surface hidden w-60 shrink-0 border-r md:flex md:flex-col">
      <div className="p-5">
        <span className="text-lg font-semibold tracking-tight">Gym</span>
      </div>
      <nav className="flex flex-col gap-1 px-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-[var(--radius-button)] px-3 py-2 text-sm font-medium",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:bg-surface-elevated hover:text-text",
              )}
            >
              <Icon className="h-5 w-5" aria-hidden />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
