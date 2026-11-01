"use client";

import { Menu } from "@base-ui/react/menu";
import { Check, ChevronDown } from "lucide-react";
import { learningGroups } from "@/lib/vocabulary-groups";

export function GroupFilter({
  value,
  onValueChange,
  label = "Groups",
  allLabel = "All groups",
  options = learningGroups,
}: {
  value: string[];
  onValueChange: (value: string[]) => void;
  label?: string;
  allLabel?: string;
  options?: readonly { slug: string; label: string }[];
}) {
  const selectedLabels = options
    .filter((group) => value.includes(group.slug))
    .map((group) => group.label);

  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label={`Filter ${label.toLowerCase()}: ${selectedLabels.join(", ") || allLabel}`}
        className={`flex h-7 w-full cursor-pointer items-center justify-between gap-1 bg-transparent text-sm font-normal outline-none hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 ${value.length ? "text-emerald-700" : "text-stone-900"}`}
      >
        {label}
        <ChevronDown aria-hidden="true" className="size-3 shrink-0" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner align="end" sideOffset={6} className="z-50">
          <Menu.Popup className="max-h-[var(--available-height)] w-44 overflow-y-auto rounded-xl border border-stone-200 bg-white p-1.5 text-sm text-stone-900 shadow-[0_2px_4px_rgb(0_0_0/0.06),0_8px_24px_rgb(0_0_0/0.1)] outline-none">
              {[
                { slug: "", label: allLabel },
                ...options,
              ].map((group) => (
                <Menu.CheckboxItem
                  key={group.slug}
                  checked={group.slug ? value.includes(group.slug) : value.length === 0}
                  onCheckedChange={(checked) => {
                    if (!group.slug) {
                      onValueChange([]);
                      return;
                    }
                    const next = new Set(value);
                    if (checked) next.add(group.slug);
                    else next.delete(group.slug);
                    onValueChange(options.filter((item) => next.has(item.slug)).map((item) => item.slug));
                  }}
                  label={group.label}
                  closeOnClick={false}
                  className="group/filter-option flex min-h-9 cursor-pointer items-center gap-2 rounded-lg px-2 py-2 outline-none data-highlighted:bg-stone-100"
                >
                  <span
                    aria-hidden="true"
                    className="flex size-4 shrink-0 items-center justify-center rounded-[3px] border border-stone-300 bg-white group-data-checked/filter-option:border-emerald-700 group-data-checked/filter-option:bg-emerald-700 group-data-checked/filter-option:text-white"
                  >
                    <Menu.CheckboxItemIndicator>
                      <Check className="size-3" strokeWidth={3} />
                    </Menu.CheckboxItemIndicator>
                  </span>
                  <span>{group.label}</span>
                </Menu.CheckboxItem>
              ))}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
