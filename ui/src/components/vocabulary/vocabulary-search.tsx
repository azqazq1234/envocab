"use client";

import { useEffect, useState } from "react";
import { Combobox } from "@base-ui/react/combobox";
import { Search, X } from "lucide-react";
import { getWordPage, type SavedWord } from "@/lib/vocabulary-api";

export function VocabularySearch({
  groupSlug,
  groupLabel,
  onSelect,
  memberOf,
  seniorTypes,
}: {
  groupSlug: string;
  memberOf?: string[];
  seniorTypes?: string[];
  groupLabel: string;
  onSelect: (word: SavedWord) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const search = query.trim();
  const [result, setResult] = useState<{
    key: string;
    words: SavedWord[];
    error: string;
  }>({ key: "", words: [], error: "" });
  const membershipKey = memberOf?.join(",") ?? "";
  const typesKey = seniorTypes?.join(",") ?? "";
  const key = `${groupSlug}:${membershipKey}:${typesKey}:${search}`;
  const loading = search.length > 0 && result.key !== key;
  const words = result.key === key ? result.words : [];

  useEffect(() => {
    if (!search) return;
    const request = new AbortController();
    const timer = setTimeout(() => {
      getWordPage(
        { group: groupSlug, memberOf: membershipKey ? membershipKey.split(",") : undefined, seniorTypes: typesKey ? typesKey.split(",") : undefined, search, pageSize: 8, sortBy: "english" },
        request.signal,
      )
        .then((data) => {
          if (!request.signal.aborted)
            setResult({ key, words: data.items, error: "" });
        })
        .catch((cause: unknown) => {
          if (!request.signal.aborted)
            setResult({
              key,
              words: [],
              error:
                cause instanceof Error ? cause.message : "Unable to search.",
            });
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      request.abort();
    };
  }, [groupSlug, membershipKey, typesKey, search, key]);

  return (
    <Combobox.Root<SavedWord>
      items={words}
      filter={null}
      value={null}
      inputValue={query}
      onInputValueChange={(value, details) => {
        setQuery(details.reason === "item-press" ? "" : value);
      }}
      open={open && search.length > 0}
      onOpenChange={setOpen}
      itemToStringLabel={(word) => word.term}
      isItemEqualToValue={(word, selected) => word.id === selected.id}
      autoHighlight
      onValueChange={(word) => {
        if (word) {
          setOpen(false);
        }
      }}
    >
      <div className="relative w-full min-w-0">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-stone-400"
        />
        <Combobox.Input
          aria-label={`Search ${groupLabel} words in English or Chinese`}
          placeholder="Search"
          autoComplete="off"
          maxLength={200}
          className="h-9 w-full rounded-lg border-0 bg-white pr-9 pl-9 text-sm shadow-[0_2px_3px_rgba(0,0,0,0.04),0_6px_14px_-6px_rgba(0,0,0,0.2)] outline-none placeholder:text-stone-400 focus-visible:shadow-[0_2px_4px_rgba(0,0,0,0.06),0_6px_16px_-6px_rgba(0,0,0,0.25)]"
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear search"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              setQuery("");
              setOpen(false);
            }}
            className="absolute top-1/2 right-2 flex size-6 -translate-y-1/2 cursor-pointer items-center justify-center text-stone-400 hover:text-stone-600"
          >
            <X aria-hidden="true" className="size-3.5" />
          </button>
        ) : null}
      </div>
      <Combobox.Portal>
        <Combobox.Positioner sideOffset={8} align="start" className="z-50">
          <Combobox.Popup className="w-[var(--anchor-width)] min-w-0 max-w-[var(--anchor-width)] overflow-hidden rounded-xl bg-white p-1 shadow-[0_8px_32px_rgba(0,0,0,0.14)] ring-1 ring-black/5">
            {loading ? (
              <p role="status" className="px-3 py-4 text-sm text-stone-500">
                Searching…
              </p>
            ) : result.error && result.key === key ? (
              <p role="alert" className="px-3 py-4 text-sm text-red-600">
                {result.error}
              </p>
            ) : words.length === 0 ? (
              <p role="status" className="px-3 py-4 text-sm text-stone-500">
                No matching words.
              </p>
            ) : null}
            <Combobox.List className="max-h-72 overflow-y-auto overscroll-contain">
              {(word: SavedWord) => (
                <Combobox.Item
                  key={word.id}
                  value={word}
                  onClick={() => {
                    onSelect(word);
                    setQuery("");
                    setOpen(false);
                  }}
                  className="flex cursor-pointer flex-col gap-1 rounded-lg px-3 py-2 outline-none data-highlighted:bg-emerald-50"
                >
                  <span className="text-sm font-semibold text-emerald-700">
                    {word.term}
                  </span>
                  <span
                    lang="zh-CN"
                    className="line-clamp-2 text-xs text-stone-500"
                  >
                    {word.meanings
                      .map((meaning) => meaning.meaning)
                      .join(" · ")}
                  </span>
                </Combobox.Item>
              )}
            </Combobox.List>
          </Combobox.Popup>
        </Combobox.Positioner>
      </Combobox.Portal>
    </Combobox.Root>
  );
}
