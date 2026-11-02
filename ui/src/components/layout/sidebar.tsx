"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GraduationCap,
  Layers,
  School,
  FileText,
  Files,
  LibraryBig,
  Globe,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";
import { vocabularyGroups } from "@/lib/vocabulary-groups";

const groupIcons = {
  all: Layers,
  junior: GraduationCap,
  senior: School,
  cet4: FileText,
  cet6: Files,
  postgraduate: LibraryBig,
  ielts: Globe,
  coca: LibraryBig,
};

const groups = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  ...vocabularyGroups.map((group) => ({
    href: `/${group.slug}`,
    label: group.label,
    icon: groupIcons[group.slug],
  })),
];

export function SidebarNavigation({ collapsed = false, onNavigate, id }: {
  collapsed?: boolean;
  onNavigate?: () => void;
  id: string;
}) {
  const pathname = usePathname();

  return (
      <nav
        id={id}
        aria-label="Sidebar navigation"
        className="min-h-0 flex-1 overflow-y-auto"
      >
        <div className="flex flex-col gap-1">
          {groups.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href ||
              pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                aria-label={label}
                title={collapsed ? label : undefined}
                className={cn(
                  "flex h-12 shrink-0 items-center rounded-xl text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700",
                  collapsed ? "justify-center" : "pr-3",
                  active
                    ? "bg-emerald-50 text-emerald-800"
                    : "text-stone-600 hover:bg-stone-100 hover:text-stone-900",
                )}
              >
                <span className="flex w-12 shrink-0 justify-center">
                  <Icon aria-hidden="true" className="size-5 shrink-0" />
                </span>
                {!collapsed ? (
                  <span className="flex flex-col items-start gap-0.5">
                    <span className="font-medium">{label}</span>
                  </span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </nav>
  );
}

export function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <aside
      className={cn(
        "fixed bottom-0 left-0 top-14 z-30 hidden flex-col border-r bg-background pt-1 pl-2 pr-[7px] transition-[width] duration-200 motion-reduce:transition-none sm:flex",
        collapsed ? "w-16" : "w-56",
      )}
    >
      <SidebarNavigation id="sidebar-navigation" collapsed={collapsed} />
      <div
        className={cn(
          "mt-4 flex h-[var(--app-footer-height)] shrink-0 items-center border-t",
          collapsed ? "justify-center" : "justify-end",
        )}
      >
        <IconButton
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          aria-controls="sidebar-navigation"
        >
          {collapsed ? (
            <PanelLeftOpen aria-hidden="true" />
          ) : (
            <PanelLeftClose aria-hidden="true" />
          )}
        </IconButton>
      </div>
    </aside>
  );
}
