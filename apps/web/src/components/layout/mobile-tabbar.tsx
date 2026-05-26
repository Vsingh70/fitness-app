"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/cn";

export function MobileTabBar() {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((item) => item.mobileVisible);

  return (
    <nav className="border-border bg-surface/95 fixed right-0 bottom-0 left-0 z-30 border-t backdrop-blur md:hidden">
      <ul className="flex h-16 items-stretch">
        {items.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                className={cn(
                  "flex h-full w-full flex-col items-center justify-center gap-1 text-xs",
                  active ? "text-accent" : "text-text-secondary",
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
