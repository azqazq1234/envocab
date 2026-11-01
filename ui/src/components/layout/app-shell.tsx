"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";

const narrowViewportQuery = "(width < 640px)";

function subscribeToViewport(onChange: () => void) {
  const media = window.matchMedia(narrowViewportQuery);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

function isNarrowViewport() {
  return window.matchMedia(narrowViewportQuery).matches;
}

function serverViewport() {
  return false;
}

export function AppShell({ children }: { children: ReactNode }) {
  const narrow = useSyncExternalStore(subscribeToViewport, isNarrowViewport, serverViewport);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [mobileExpanded, setMobileExpanded] = useState(false);
  const collapsed = narrow ? !mobileExpanded : desktopCollapsed;

  return (
    <>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => {
          if (narrow) setMobileExpanded((value) => !value);
          else setDesktopCollapsed((value) => !value);
        }}
      />
      <main
        id="main-content"
        tabIndex={-1}
        className={cn(
          "min-h-dvh pt-14 transition-[margin-left] duration-200 motion-reduce:transition-none",
          collapsed ? "ml-16" : "ml-40 sm:ml-56",
        )}
      >
        {children}
      </main>
    </>
  );
}
