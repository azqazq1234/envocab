"use client";

import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <main
        id="main-content"
        tabIndex={-1}
        className={cn(
          "min-h-dvh transition-[margin-left] duration-200 motion-reduce:transition-none sm:pt-14",
          collapsed ? "sm:ml-16" : "sm:ml-56",
        )}
      >
        {children}
      </main>
    </>
  );
}
