import type { ReactNode } from "react";

import { DesktopSidebar } from "@/components/layout/desktop-sidebar";
import { MobileTabBar } from "@/components/layout/mobile-tabbar";
import { TopBar } from "@/components/layout/top-bar";
import { ToastViewport } from "@/components/ui/toast";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <DesktopSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 px-4 pt-4 pb-24 md:px-8 md:pb-8">{children}</main>
      </div>
      <MobileTabBar />
      <ToastViewport />
    </div>
  );
}
