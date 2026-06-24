"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";

import { ReconnectBanner } from "@/components/health/reconnect-banner";
import { DesktopSidebar } from "@/components/layout/desktop-sidebar";
import { MobileTabBar } from "@/components/layout/mobile-tabbar";
import { TopBar } from "@/components/layout/top-bar";
import { TutorialHost } from "@/components/tutorial/tutorial-host";
import { ToastViewport } from "@/components/ui/toast";
import { SessionStickyBar } from "@/components/workouts/session-sticky-bar";
import { installAudioUnlock } from "@/lib/audio/unlock";
import { useApplyTheme } from "@/lib/hooks/use-theme";
import { installOnlineFlush } from "@/lib/offline/queue";

export default function AppShell({ children }: { children: ReactNode }) {
  useApplyTheme();

  useEffect(() => {
    const unlockOff = installAudioUnlock();
    const flushOff = installOnlineFlush();
    return () => {
      unlockOff();
      flushOff();
    };
  }, []);

  return (
    <div className="flex min-h-screen">
      <DesktopSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar workoutInProgressSlot={<SessionStickyBar />} />
        <main className="page-shell flex-1 pt-4 pb-24 md:pb-8">
          <ReconnectBanner />
          {children}
        </main>
      </div>
      <MobileTabBar />
      <ToastViewport />
      <TutorialHost />
    </div>
  );
}
