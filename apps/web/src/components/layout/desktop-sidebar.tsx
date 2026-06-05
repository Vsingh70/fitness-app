"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/cn";

export function DesktopSidebar() {
  const pathname = usePathname();
  return (
    <aside className="border-border bg-surface sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col border-r px-4 pt-6 pb-[18px] md:flex">
      <div className="flex items-center gap-[11px] px-2 pb-[22px]">
        <span
          className="bg-accent text-accent-foreground font-serif grid h-[30px] w-[30px] place-items-center rounded-[3px] text-base font-semibold tracking-tight"
          aria-hidden
        >
          V
        </span>
        <span className="font-serif text-[19px] font-medium tracking-tight">VGains</span>
      </div>
      <nav className="flex flex-col gap-px">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-[var(--radius-button)] px-[10px] py-[9px] text-sm font-medium transition-colors duration-150 ease-out",
                active
                  ? "bg-surface-elevated text-text font-semibold shadow-[inset_2px_0_0_var(--color-accent)]"
                  : "text-text-secondary hover:bg-surface-elevated hover:text-text",
              )}
            >
              <Icon className="h-[18px] w-[18px]" aria-hidden />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
