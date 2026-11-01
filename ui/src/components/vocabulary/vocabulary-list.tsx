"use client";

import dynamic from "next/dynamic";
import { Triangle } from "lucide-react";
import type { WordActionMode } from "@/components/vocabulary/word-dialog";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { VocabularyPagination } from "@/components/vocabulary/vocabulary-pagination";
import { Checkbox } from "@/components/ui/checkbox";
import { WordActions } from "@/components/vocabulary/word-actions";
import { LearningScore } from "@/components/vocabulary/learning-score";
import { WordMeanings } from "./word-meanings";
import {
  useVocabularyList,
  type WordFocusTarget,
} from "@/hooks/use-vocabulary-list";
import { groupAbbreviations, seniorTypes } from "@/lib/vocabulary-groups";
import { GroupFilter } from "./group-filter";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SavedWord } from "@/lib/vocabulary-api";

const WordDialog = dynamic(() =>
  import("./word-dialog").then((module) => module.WordDialog),
);

const selectionCheckboxClassName =
  "cursor-pointer data-checked:border-emerald-600 data-checked:bg-emerald-600 data-checked:text-white data-indeterminate:border-emerald-600 data-indeterminate:bg-emerald-600 data-indeterminate:text-white dark:data-checked:bg-emerald-600";

export function VocabularyList({
  groupSlug,
  groupLabel,
  additionRevision,
  onTotalChange,
  focusTarget,
  groupFilter,
  onGroupFilterChange,
  typeFilter,
  onTypeFilterChange,
}: {
  groupSlug: string;
  groupLabel: string;
  additionRevision: number;
  onTotalChange: (total: number) => void;
  focusTarget: WordFocusTarget;
  groupFilter: string[];
  onGroupFilterChange: (value: string[]) => void;
  typeFilter: string[];
  onTypeFilterChange: (value: string[]) => void;
}) {
  const [action, setAction] = useState<{
    word: SavedWord;
    mode: WordActionMode;
  } | null>(null);
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const {
    scrollRef,
    data,
    error,
    loading,
    measuring,
    words,
    empty,
    currentPage,
    totalPages,
    pageSize,
    sort,
    navigateToPage,
    changeSort,
    changePageSize,
    refresh,
  } = useVocabularyList({
    groupSlug,
    additionRevision,
    focusTarget,
    onTotalChange,
    memberOf: groupFilter.length ? groupFilter : undefined,
    seniorTypes: typeFilter.length ? typeFilter : undefined,
  });
  const selectedOnPage = words.filter((word) => selected.has(word.id)).length;
  const allSelected = words.length > 0 && selectedOnPage === words.length;
  const showClassification = groupSlug === "all" || groupSlug === "senior";
  const showEmpty = empty && !measuring;

  function toggleRows(ids: number[], checked: boolean) {
    setSelected((previous) => {
      const next = new Set(previous);
      for (const id of ids) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  function refreshAfterChange(id: number, deleted: boolean) {
    if (deleted) {
      toggleRows([id], false);
      if (words.length === 1 && currentPage > 1)
        navigateToPage(currentPage - 1);
    }
    refresh();
  }

  return (
    <div
      className="vocabulary-list flex h-full min-h-0 flex-col overflow-hidden rounded-xl bg-white"
      data-show-groups={groupSlug === "all"}
      data-show-types={groupSlug === "senior"}
      aria-busy={loading}
    >
      <div
        className="vocabulary-table-viewport relative min-h-0 flex-1 overflow-hidden"
        data-empty={showEmpty}
      >
        <div
          ref={scrollRef}
          className={`h-full overflow-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [&_[data-slot=table-container]]:overflow-visible ${showEmpty ? "[&_[data-slot=table-container]]:h-full" : ""}`}
        >
          <Table
            className={`vocabulary-table table-fixed min-w-[calc(var(--fixed-width)+max(var(--chinese-min-width),var(--chinese-content-width,0px)))] ${showEmpty ? "h-full" : ""}`}
            aria-label={`${groupLabel} vocabulary list`}
          >
            <colgroup>
              <col className="w-[var(--selection-width)]" />
              <col className="w-[var(--score-width)]" />
              <col className="w-[var(--english-width)]" />
              <col />
              {showClassification ? (
                <col className="w-[var(--groups-width)]" />
              ) : null}
              <col className="w-[var(--actions-width)]" />
            </colgroup>
            <TableHeader className="h-10 [&_th]:text-sm [&_th]:font-normal">
              <TableRow className="hover:bg-transparent">
                <TableHead scope="col">
                  <Checkbox
                    aria-label="Select all words on this page"
                    className={selectionCheckboxClassName}
                    disabled={empty}
                    checked={allSelected}
                    indeterminate={selectedOnPage > 0 && !allSelected}
                    onCheckedChange={(checked) =>
                      toggleRows(
                        words.map((word) => word.id),
                        checked,
                      )
                    }
                  />
                </TableHead>
                <TableHead scope="col">Score</TableHead>
                <TableHead
                  scope="col"
                  aria-sort={
                    sort === null
                      ? "none"
                      : sort === "asc"
                        ? "ascending"
                        : "descending"
                  }
                >
                  <div className="group/sort flex w-fit items-center gap-1">
                    <button
                      type="button"
                      className="h-10 cursor-pointer rounded-sm hover:text-emerald-700 focus-visible:outline-2 focus-visible:outline-emerald-700"
                      onClick={() => changeSort(null)}
                      aria-label="Restore original word order"
                      title="Original order"
                    >
                      English
                    </button>
                    <button
                      type="button"
                      className={`flex size-6 cursor-pointer items-center justify-center rounded-sm transition-opacity hover:text-emerald-700 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-emerald-700 ${sort === null ? "text-muted-foreground opacity-0 group-hover/sort:opacity-100 group-focus-within/sort:opacity-100" : "text-emerald-700 opacity-100"}`}
                      onClick={() =>
                        changeSort(sort === "asc" ? "desc" : "asc")
                      }
                      aria-label={`Sort English ${sort === "asc" ? "descending" : "ascending"}`}
                      title={sort === "asc" ? "Descending" : "Ascending"}
                    >
                      <Triangle
                        aria-hidden="true"
                        className={`size-2 fill-current ${sort === "asc" ? "rotate-180" : ""}`}
                      />
                    </button>
                  </div>
                </TableHead>
                <TableHead scope="col">Chinese</TableHead>
                {groupSlug === "all" ? (
                  <TableHead scope="col">
                    <GroupFilter
                      value={groupFilter}
                      onValueChange={onGroupFilterChange}
                    />
                  </TableHead>
                ) : null}
                {groupSlug === "senior" ? (
                  <TableHead scope="col">
                    <GroupFilter
                      label="Types"
                      allLabel="All types"
                      options={seniorTypes}
                      value={typeFilter}
                      onValueChange={onTypeFilterChange}
                    />
                  </TableHead>
                ) : null}
                <TableHead scope="col" className="pr-0">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="[&_td]:py-1 [&_tr:last-child]:border-b">
              {measuring ? (
                <TableRow data-page-size-probe="" aria-hidden="true" className="invisible">
                  <TableCell colSpan={showClassification ? 6 : 5}>
                    {/* Match the 8-unit action controls plus real cell padding/borders. */}
                    <div className="h-8" />
                  </TableCell>
                </TableRow>
              ) : empty ? (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={showClassification ? 6 : 5}
                    className="text-center align-middle text-muted-foreground"
                  >
                    {!loading && error ? (
                      <div role="alert">
                        {error}
                        <Button
                          variant="link"
                          className="cursor-pointer"
                          onClick={refresh}
                        >
                          Retry
                        </Button>
                      </div>
                    ) : null}
                  </TableCell>
                </TableRow>
              ) : (
                words.map((word) => {
                  const visibleGroups = groupFilter.length
                    ? word.groups.filter((group) => groupFilter.includes(group.slug))
                    : word.groups;
                  return (
                    <TableRow
                      key={word.id}
                      className="group/word outline-none hover:bg-emerald-50 data-[state=selected]:bg-emerald-50"
                      data-word-id={word.id}
                      tabIndex={-1}
                      data-state={
                        selected.has(word.id) ? "selected" : undefined
                      }
                    >
                      <TableCell>
                        <Checkbox
                          aria-label={`Select ${word.term}`}
                          className={selectionCheckboxClassName}
                          checked={selected.has(word.id)}
                          onCheckedChange={(checked) =>
                            toggleRows([word.id], checked)
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <LearningScore score={0} />
                      </TableCell>
                      <TableCell>
                        <p className="truncate font-medium" title={word.term}>
                          {word.term}
                        </p>
                      </TableCell>
                      <TableCell>
                        <div
                          className="w-max whitespace-nowrap"
                          data-chinese-content=""
                          title={word.meanings
                            .map((meaning) => meaning.meaning)
                            .join(" · ")}
                        >
                          <WordMeanings meanings={word.meanings} inline />
                        </div>
                      </TableCell>
                      {groupSlug === "all" ? (
                        <TableCell>
                          <div className="flex w-max flex-nowrap items-center gap-1">
                            {visibleGroups.length > 0
                              ? visibleGroups.map((group) => (
                                  <span
                                    key={group.slug}
                                    title={group.name}
                                    aria-label={group.name}
                                    className="inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-emerald-100 px-1 py-0 align-middle text-xs leading-none font-medium text-emerald-800"
                                  >
                                    {groupAbbreviations[group.slug] ??
                                      group.name.toUpperCase()}
                                  </span>
                                ))
                              : "—"}
                          </div>
                        </TableCell>
                      ) : null}
                      {groupSlug === "senior" ? (
                        <TableCell>
                          <div className="flex flex-wrap items-center gap-1">
                            {word.senior_types?.length ? word.senior_types.map((type) => (
                              <span key={type} className="inline-flex h-5 items-center justify-center rounded-full bg-emerald-700 px-1.5 py-0 align-middle text-xs leading-none font-medium text-white">
                                {type}
                              </span>
                            )) : "—"}
                          </div>
                        </TableCell>
                      ) : null}
                      <TableCell className="px-0">
                        <WordActions
                          term={word.term}
                          onEdit={() => setAction({ word, mode: "edit" })}
                          onDelete={() => setAction({ word, mode: "delete" })}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      <VocabularyPagination
        page={currentPage}
        pageSize={pageSize}
        totalPages={totalPages}
        totalWords={data?.total ?? 0}
        selectedCount={selected.size}
        loading={loading}
        onPageChange={navigateToPage}
        onPageSizeChange={changePageSize}
      />
      {action ? (
        <WordDialog
          word={action.word}
          mode={action.mode}
          groupSlug={groupSlug}
          groupLabel={groupLabel}
          onClose={() => setAction(null)}
          onChanged={refreshAfterChange}
        />
      ) : null}
    </div>
  );
}
