"use client";

import { useEffect, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { BookOpen } from "lucide-react";
import { SidebarNavigation } from "@/components/layout/sidebar";

export function MobileNavigation() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 640px)");
    const closeOnDesktop = () => { if (desktop.matches) setOpen(false); };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger
        aria-label="Open navigation"
        className="flex size-10 cursor-pointer items-center justify-center rounded-xl bg-emerald-700 text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
      >
        <BookOpen aria-hidden="true" className="size-5" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-transparent sm:hidden" />
        <Dialog.Popup className="fixed inset-y-0 left-0 z-60 flex w-max max-w-[calc(100vw-3rem)] flex-col bg-white pb-[env(safe-area-inset-bottom)] shadow-xl outline-none transition-transform duration-200 ease-out data-starting-style:-translate-x-full data-ending-style:-translate-x-full motion-reduce:transition-none sm:hidden">
          <div className="flex h-16 shrink-0 items-center justify-between pr-4 pl-5.5">
            <Dialog.Title className="font-semibold tracking-widest text-emerald-700">VOCAB</Dialog.Title>
          </div>
          <Dialog.Description className="sr-only">Choose a vocabulary group or open the dashboard.</Dialog.Description>
          <div className="flex min-h-0 flex-1 flex-col px-2 pb-3 [&_nav_a]:pr-3.5">
            <SidebarNavigation id="mobile-sidebar-navigation" onNavigate={() => setOpen(false)} />
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
