"use client";

import { Menu } from "@base-ui/react/menu";
import { useRef } from "react";
import {
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { PAGE_SIZES } from "@/lib/vocabulary-layout";

function pageItems(page: number, totalPages: number): (number | string)[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }
  const start =
    page <= 4 ? 2 : page >= totalPages - 3 ? totalPages - 4 : page - 1;
  const end =
    page <= 4 ? 5 : page >= totalPages - 3 ? totalPages - 1 : page + 1;
  return [
    1,
    ...(start > 2 ? ["start-ellipsis"] : []),
    ...Array.from({ length: end - start + 1 }, (_, index) => start + index),
    ...(end < totalPages - 1 ? ["end-ellipsis"] : []),
    totalPages,
  ];
}

export function VocabularyPagination({
  page,
  pageSize,
  totalPages,
  totalWords,
  selectedCount,
  loading,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  totalPages: number;
  totalWords: number;
  selectedCount: number;
  loading: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const pageSizeIconRef = useRef<SVGSVGElement>(null);
  const compactStart = Math.max(1, Math.min(page - 1, totalPages - 2));

  return (
    <div className="@container/pagination grid h-[var(--app-footer-height)] shrink-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 border-t text-sm text-muted-foreground">
      <span aria-live="polite" className="min-w-0 truncate pl-2 whitespace-nowrap">
        {totalWords} words
        {selectedCount > 0 ? ` · ${selectedCount} selected` : ""}
      </span>
      <nav
        aria-label="Vocabulary pagination"
        className="col-start-2 row-start-1 flex min-w-0 items-center justify-center gap-1 overflow-hidden @max-[680px]/pagination:gap-0.5"
      >
        <IconButton
          aria-label="First page"
          title="First page"
          className="@max-[680px]/pagination:hidden"
          disabled={loading || page <= 1}
          onClick={() => onPageChange(1)}
        >
          <ChevronFirst aria-hidden="true" />
        </IconButton>
        <IconButton
          aria-label="Previous page"
          title="Previous page"
          disabled={loading || page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
        </IconButton>
        {pageItems(page, totalPages).map((item) =>
          typeof item === "number" ? (
            <Button
              key={item}
              variant="ghost"
              size="icon"
              aria-label={`Page ${item}`}
              aria-current={item === page ? "page" : undefined}
              disabled={loading}
              onClick={() => onPageChange(item)}
              className={`cursor-pointer border-0 bg-transparent hover:bg-transparent ${item < compactStart || item > compactStart + 2 ? "@max-[680px]/pagination:hidden" : ""} ${item === page ? "font-semibold text-foreground" : "font-normal text-muted-foreground"}`}
            >
              {item}
            </Button>
          ) : (
            <span
              key={item}
              aria-hidden="true"
              className="flex size-8 shrink-0 items-center justify-center @max-[680px]/pagination:hidden"
            >
              …
            </span>
          ),
        )}
        <IconButton
          aria-label="Next page"
          title="Next page"
          disabled={loading || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight aria-hidden="true" />
        </IconButton>
        <IconButton
          aria-label="Last page"
          title="Last page"
          className="@max-[680px]/pagination:hidden"
          disabled={loading || page >= totalPages}
          onClick={() => onPageChange(totalPages)}
        >
          <ChevronLast aria-hidden="true" />
        </IconButton>
      </nav>
      <div className="col-start-3 row-start-1 w-[calc(var(--actions-width)+var(--actions-column-right,0px))] min-w-24 justify-self-end pl-2 pr-[calc(var(--actions-column-right,0px)+var(--spacing)*2)] @max-[400px]/pagination:w-full @max-[400px]/pagination:min-w-0 @max-[400px]/pagination:px-1">
        <Menu.Root>
          <Menu.Trigger
            aria-label={`Rows per page: ${pageSize}`}
            disabled={loading}
            className="flex h-7 w-full cursor-pointer items-center justify-between gap-1 bg-transparent text-sm font-normal text-muted-foreground outline-none hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="whitespace-nowrap">{pageSize}<span className="@max-[400px]/pagination:hidden"> / page</span></span>
            <ChevronDown ref={pageSizeIconRef} aria-hidden="true" className="size-3 shrink-0" />
          </Menu.Trigger>
          <Menu.Portal>
            <Menu.Positioner anchor={pageSizeIconRef} side="top" align="end" sideOffset={14} className="z-50">
              <Menu.Popup className="max-h-[var(--available-height)] w-44 overflow-y-auto rounded-xl border border-stone-200 bg-white p-1.5 text-sm text-stone-900 shadow-[0_2px_4px_rgb(0_0_0/0.06),0_8px_24px_rgb(0_0_0/0.1)] outline-none">
                <Menu.RadioGroup value={pageSize} onValueChange={onPageSizeChange}>
                  {PAGE_SIZES.map((size) => (
                    <Menu.RadioItem
                      key={size}
                      value={size}
                      label={`${size} / page`}
                      closeOnClick
                      className="flex min-h-9 cursor-pointer items-center rounded-lg px-2 py-2 outline-none data-checked:font-medium data-checked:text-emerald-700 data-highlighted:bg-stone-100"
                    >
                      <span>{size} / page</span>
                    </Menu.RadioItem>
                  ))}
                </Menu.RadioGroup>
              </Menu.Popup>
            </Menu.Positioner>
          </Menu.Portal>
        </Menu.Root>
      </div>
    </div>
  );
}
