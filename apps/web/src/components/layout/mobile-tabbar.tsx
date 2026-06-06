"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/cn";

export function MobileTabBar() {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((item) => item.mobileVisible);

  return (
    <nav className="border-border bg-bg/[0.86] fixed right-0 bottom-0 left-0 z-30 border-t backdrop-blur-xl backdrop-saturate-150 md:hidden">
      <ul className="grid h-16 grid-cols-5 px-2 pt-2 pb-3">
        {items.map(({ href, label, icon: Icon, tutorialId }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                data-tutorial={tutorialId}
                className={cn(
                  "flex h-full w-full flex-col items-center justify-center gap-[3px] text-[9px] font-semibold uppercase tracking-[0.06em]",
                  active ? "text-text" : "text-text-tertiary",
                )}
              >
                <Icon className="h-5 w-5" aria-hidden />
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
