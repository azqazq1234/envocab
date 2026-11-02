"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { useGroupProgress } from "@/hooks/use-group-progress";
import { PageHeader } from "@/components/layout/page-header";
import { AddWordDialog } from "@/components/vocabulary/add-word-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useState } from "react";
import { VocabularyList } from "@/components/vocabulary/vocabulary-list";
import { VocabularyCheck } from "@/components/vocabulary/vocabulary-check";
import { VocabularySearch } from "@/components/vocabulary/vocabulary-search";

export function VocabularyTabs({
  groupLabel,
  groupSlug,
}: {
  groupLabel: string;
  groupSlug: string;
}) {
  const { user } = useAuth();
  const [view, setView] = useState("check");
  const [revision, setRevision] = useState(0);
  const [checkRevision, setCheckRevision] = useState(0);
  const [focusTarget, setFocusTarget] = useState<{
    id: number;
    revision: number;
  } | null>(null);
  const [groupFilter, setGroupFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);

  const { groups } = useGroupProgress(revision, groupSlug === "all");
  const groupProgress = groups?.find((group) => group.slug === groupSlug);
  const completion = groupProgress?.completion;
  const percent = completion === undefined ? null : Math.round(completion);

  return (
    <Tabs
      value={view}
      onValueChange={(value) => setView(String(value))}
      className="@container/vocabulary h-full min-h-0 gap-0"
    >
      <PageHeader title={groupLabel} titleId="vocabulary-title">
        <TabsList
          variant="line"
          className="order-2 grid h-8 w-auto shrink-0 grid-cols-2 gap-5 p-0 group-data-horizontal/tabs:h-8 @[1100px]/vocabulary:h-full @[1100px]/vocabulary:w-full @[1100px]/vocabulary:gap-0 @[1100px]/vocabulary:group-data-horizontal/tabs:h-full"
          aria-label={`${groupLabel} vocabulary views`}
        >
          {(
            [
              ["check", "Check"],
              ["list", "List"],
            ] as const
          ).map(([value, label]) => (
            <TabsTrigger
              key={value}
              value={value}
              onClick={() => {
                if (value === "check" && view === "check")
                  setCheckRevision((revision) => revision + 1);
              }}
              className="h-8 w-max flex-none cursor-pointer self-center justify-self-center rounded-none border-x-0 px-0 py-0 text-sm group-data-horizontal/tabs:after:bottom-[-1px] group-data-horizontal/tabs:after:h-1 after:bg-emerald-700"
            >
              {label}
            </TabsTrigger>
          ))}
        </TabsList>
        <div
          className="order-3 flex w-40 max-w-full shrink-0 items-center gap-2 @[1100px]/vocabulary:w-auto @[1100px]/vocabulary:min-w-0 @[1100px]/vocabulary:pr-6"
          title="Group learning progress"
        >
          <div
            role="progressbar"
            aria-label={`${groupLabel} learning progress`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent ?? undefined}
            className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-emerald-100"
          >
            <div
              className="h-full rounded-full bg-emerald-700"
              style={{ width: `${completion ?? 0}%` }}
            />
          </div>
          <span className="shrink-0 text-sm text-stone-500 tabular-nums">
            {percent === null ? "—" : `${percent}%`}
          </span>
        </div>
        {view === "list" ? (
          <div className="order-5 flex w-full min-w-0 basis-full justify-center [&>div]:w-4/5 @[1100px]/vocabulary:col-start-5 @[1100px]/vocabulary:basis-auto @[1100px]/vocabulary:[&>div]:w-full">
            <VocabularySearch
              groupSlug={groupSlug}
              memberOf={groupFilter}
              seniorTypes={typeFilter}
              groupLabel={groupLabel}
              onSelect={(word) => {
                setFocusTarget((previous) => ({
                  id: word.id,
                  revision: (previous?.revision ?? 0) + 1,
                }));
                setView("list");
              }}
            />
          </div>
        ) : null}
        {user?.is_admin && groupSlug !== "all" ? (
          <div className="order-4 ml-auto size-9 shrink-0 @[1100px]/vocabulary:absolute @[1100px]/vocabulary:top-2.5 @[1100px]/vocabulary:right-2.5">
            <AddWordDialog
              groupLabel={groupLabel}
              groupSlug={groupSlug}
              onAdded={() => {
                setFocusTarget(null);
                setRevision((value) => value + 1);
                setView("list");
              }}
            />
          </div>
        ) : null}
      </PageHeader>
      <TabsContent value="check" hidden={view !== "check"} className="min-h-0">
        {view === "check" ? (
          <VocabularyCheck
            requestRevision={checkRevision}
            groupSlug={groupSlug}
          />
        ) : null}
      </TabsContent>
      <TabsContent value="list" hidden={view !== "list"} className="mx-4 mt-1 min-h-0">
        <VocabularyList
          groupFilter={groupFilter}
          typeFilter={typeFilter}
          onTypeFilterChange={(value) => {
            setFocusTarget(null);
            setTypeFilter(value);
          }}
          onGroupFilterChange={(value) => {
            setFocusTarget(null);
            setGroupFilter(value);
          }}
          additionRevision={revision}
          focusTarget={focusTarget}
          groupSlug={groupSlug}
          groupLabel={groupLabel}
        />
      </TabsContent>
    </Tabs>
  );
}
