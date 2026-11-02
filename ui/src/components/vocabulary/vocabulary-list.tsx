"use client";

import { useAuth } from "@/components/auth/auth-provider";
import dynamic from "next/dynamic";
import { Triangle } from "lucide-react";
import type { WordActionMode } from "@/components/vocabulary/word-dialog";
import { Fragment, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { VocabularyPagination } from "@/components/vocabulary/vocabulary-pagination";
import { WordActions } from "@/components/vocabulary/word-actions";
import { LearningScore } from "@/components/vocabulary/learning-score";
import { WordMeanings } from "./word-meanings";
import { WordTranslation } from "./word-translation";
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

export function VocabularyList({
  groupSlug,
  groupLabel,
  additionRevision,
  focusTarget,
  groupFilter,
  onGroupFilterChange,
  typeFilter,
  onTypeFilterChange,
}: {
  groupSlug: string;
  groupLabel: string;
  additionRevision: number;
  focusTarget: WordFocusTarget;
  groupFilter: string[];
  onGroupFilterChange: (value: string[]) => void;
  typeFilter: string[];
  onTypeFilterChange: (value: string[]) => void;
}) {
  const { user, refreshProgress, progressRevision } = useAuth();
  const meaningsId = useId();
  const [expandedWord, setExpandedWord] = useState<string | null>(null);
  const [action, setAction] = useState<{
    word: SavedWord;
    mode: WordActionMode;
  } | null>(null);
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
    refreshRevision: progressRevision,
    groupSlug,
    additionRevision,
    focusTarget,
    memberOf: groupFilter.length ? groupFilter : undefined,
    seniorTypes: typeFilter.length ? typeFilter : undefined,
  });
  const showGroups = groupSlug === "all";
  const showTypes = groupSlug === "senior";
  const showClassification = showGroups || showTypes;
  const showEmpty = empty && !measuring;
  const canManage = Boolean(user?.is_admin);
  const columnCount = 3 + Number(showClassification) + Number(canManage);

  function refreshAfterChange(_id: number, deleted: boolean) {
    refreshProgress();
    if (deleted && words.length === 1 && currentPage > 1) {
      navigateToPage(currentPage - 1);
    }
  }

  return (
    <div
      className="vocabulary-list flex h-full min-h-0 flex-col overflow-hidden rounded-xl bg-white"
      data-can-manage={canManage}
      data-show-groups={showGroups}
      aria-busy={loading}
    >
      <div
        className="vocabulary-table-viewport relative min-h-0 flex-1 overflow-hidden"
      >
        <div
          ref={scrollRef}
          className={`h-full overflow-x-hidden overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [&_[data-slot=table-container]]:overflow-visible ${showEmpty ? "[&_[data-slot=table-container]]:h-full" : ""}`}
        >
          <Table
            className={`vocabulary-table table-fixed w-full ${showEmpty ? "h-full" : ""}`}
            aria-label={`${groupLabel} vocabulary list`}
          >
            <colgroup>
              <col className="w-[var(--score-width)]" />
              <col className="w-[var(--english-width)]" />
              <col />
              {showClassification ? (
                <col data-column="classification" className="w-[var(--groups-width)]" />
              ) : null}
              {canManage ? <col className="w-[var(--actions-width)]" /> : null}
            </colgroup>
            <TableHeader className="h-10 [&_th]:text-sm [&_th]:font-normal">
              <TableRow className="hover:bg-transparent">
                <TableHead scope="col" data-column="score">Score</TableHead>
                <TableHead
                  scope="col"
                  data-column="english"
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
                <TableHead scope="col" data-column="chinese">Chinese</TableHead>
                {showClassification ? (
                  <TableHead scope="col" data-column="classification">
                    <GroupFilter
                      label={showTypes ? "Types" : undefined}
                      allLabel={showTypes ? "All types" : undefined}
                      options={showTypes ? seniorTypes : undefined}
                      value={showTypes ? typeFilter : groupFilter}
                      onValueChange={showTypes ? onTypeFilterChange : onGroupFilterChange}
                    />
                  </TableHead>
                ) : null}
                {canManage ? <TableHead scope="col" data-column="actions" className="pr-0">Actions</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody className="[&_td]:py-1 [&_tr:last-child]:border-b">
              {measuring ? (
                <TableRow key="page-size-probe" data-page-size-probe="" aria-hidden="true" className="opacity-0">
                  <TableCell colSpan={columnCount}>
                    {/* Match the tallest cell in each role's rows. */}
                    <div className={canManage ? "h-8" : "h-6"} />
                  </TableCell>
                </TableRow>
              ) : empty ? (
                <TableRow key="empty" className="hover:bg-transparent">
                  <TableCell
                    colSpan={columnCount}
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
                  const expansionKey = `${groupSlug}:${currentPage}:${word.id}`;
                  const expanded = expandedWord === expansionKey;
                  const detailId = `${meaningsId}-${word.id}`;
                  return (
                    <Fragment key={word.id}>
                      <TableRow
                        className="outline-none hover:bg-emerald-50"
                        data-word-id={word.id}
                        tabIndex={-1}
                      >
                        <TableCell data-column="score">
                          <LearningScore score={word.score} />
                        </TableCell>
                        <TableCell data-column="english">
                          <p className="truncate font-medium" title={word.term}>
                            {word.term}
                          </p>
                        </TableCell>
                        <TableCell data-column="chinese">
                          <WordTranslation
                            word={word}
                            expanded={expanded}
                            detailId={detailId}
                            onToggle={() => setExpandedWord(expanded ? null : expansionKey)}
                          />
                        </TableCell>
                        {showGroups ? (
                          <TableCell data-column="classification">
                            <div className="flex flex-wrap items-center gap-1">
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
                        {showTypes ? (
                          <TableCell data-column="classification">
                            <div className="flex flex-wrap items-center gap-1">
                              {word.senior_types?.length ? word.senior_types.map((type) => (
                                <span key={type} className="inline-flex h-5 items-center justify-center rounded-full bg-emerald-700 px-1.5 py-0 align-middle text-xs leading-none font-medium text-white">
                                  {type}
                                </span>
                              )) : "—"}
                            </div>
                          </TableCell>
                        ) : null}
                        {canManage ? (
                          <TableCell data-column="actions" className="px-0">
                            <WordActions
                              term={word.term}
                              onEdit={() => setAction({ word, mode: "edit" })}
                              onDelete={() => setAction({ word, mode: "delete" })}
                            />
                          </TableCell>
                        ) : null}
                      </TableRow>
                      <TableRow id={detailId} hidden={!expanded} className="bg-emerald-50/50">
                        {/* Groups is hidden on mobile, so each layout needs a different span. */}
                        {[false, true].map((mobile) => (
                          <TableCell
                            key={String(mobile)}
                            colSpan={columnCount - Number(mobile && showGroups)}
                            className={`!whitespace-normal !py-3 ${mobile ? "sm:hidden" : "hidden sm:table-cell"}`}
                          >
                            <div className="flex min-w-0 flex-col gap-1 [overflow-wrap:anywhere] pl-[var(--score-width)] pr-[var(--actions-width)] sm:pl-[calc(var(--score-width)+var(--english-width))] sm:pr-0" aria-label={`${word.term} 中文释义`}>
                              <WordMeanings meanings={word.meanings} />
                            </div>
                          </TableCell>
                        ))}
                      </TableRow>
                    </Fragment>
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
