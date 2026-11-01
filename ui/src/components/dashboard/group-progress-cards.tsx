"use client";

import { useEffect, useState } from "react";
import { GroupCompletionChart } from "@/components/dashboard/group-completion-chart";
import { Button } from "@/components/ui/button";
import { learningGroups } from "@/lib/vocabulary-groups";
import { apiRequest, type GroupSummary } from "@/lib/vocabulary-api";
import { UNSTUDIED_COLOR } from "@/lib/learning-colors";

function GroupProgressCard({
  label,
  total,
  error,
  onRetry,
}: {
  label: string;
  total: number | null;
  error: boolean;
  onRetry: () => void;
}) {
  return (
    <article
      aria-label={`${label} vocabulary overview`}
      className="relative h-full min-h-0 min-w-0 rounded-lg bg-white [container-type:size] shadow-[0_2px_3px_rgba(0,0,0,0.04),0_8px_18px_-8px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.9)]"
    >
      <h2 className="absolute top-1 left-3 text-lg font-semibold tracking-tight text-emerald-700">
        {label}
      </h2>
      <p
        className="absolute top-1/2 left-1/4 -translate-y-1/2 text-2xl font-semibold tracking-tight text-emerald-700 tabular-nums"
        aria-label={`${label} studied words / total words`}
      >
        {total === null
          ? null
          : `0 / ${total.toLocaleString("en-US")}`}
      </p>
      <div className="absolute top-[10%] right-[10cqh] aspect-square h-[80%]">
        {error ? (
          <div
            role="alert"
            className="flex h-full flex-col items-center justify-center gap-2 text-sm text-stone-500"
          >
            <p>Unable to load</p>
            <Button
              variant="link"
              className="cursor-pointer text-emerald-700"
              onClick={onRetry}
            >
              Retry
            </Button>
          </div>
        ) : (
          <>
            <div
              role="img"
              aria-label={`${label} learning score distribution`}
              className="absolute inset-0 rounded-full"
              style={{
                background: UNSTUDIED_COLOR,
                maskImage:
                  "radial-gradient(farthest-side, transparent calc(100% - 12px), black calc(100% - 11.75px))",
                WebkitMaskImage:
                  "radial-gradient(farthest-side, transparent calc(100% - 12px), black calc(100% - 11.75px))",
              }}
            />
            <div
              className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1"
              aria-live="polite"
            >
              <span className="text-lg font-semibold tracking-tight text-emerald-700 tabular-nums">
                {total === null ? "—" : "0%"}
              </span>
            </div>
          </>
        )}
      </div>
    </article>
  );
}

export function GroupProgressCards() {
  const [totals, setTotals] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    apiRequest<GroupSummary[]>("/groups", { signal: request.signal })
      .then((groups) => {
        if (!request.signal.aborted) {
          setTotals(
            Object.fromEntries(
              groups.map((group) => [group.slug, group.total]),
            ),
          );
        }
      })
      .catch(() => {
        if (!request.signal.aborted) setError(true);
      });
    return () => request.abort();
  }, [retry]);

  function retryLoading() {
    setError(false);
    setRetry((value) => value + 1);
  }

  const chartData = learningGroups.map((group) => ({
    name: group.label,
    completion:
      totals === null
        ? null
        : 0,
  }));
  return (
    <div className="@container flex min-h-0 flex-1 flex-col gap-6 px-4 pb-[calc((var(--app-footer-height)-2rem-1px)/2)] [--dashboard-height:calc(100dvh-7rem)] @[992px]/dashboard:justify-between @[992px]/dashboard:gap-0">
      <div className="grid shrink-0 auto-rows-[calc(var(--dashboard-height)*0.2)] grid-cols-1 gap-[calc(var(--dashboard-height)*0.02)] @[600px]:grid-cols-2 @[960px]:-m-4 @[960px]:h-[calc(var(--dashboard-height)*0.42+2rem)] @[960px]:grid-cols-3 @[960px]:overflow-x-hidden @[960px]:overflow-y-auto @[960px]:p-4">
        {learningGroups.map((group) => (
          <GroupProgressCard
            key={group.slug}
            label={group.label}
            total={totals === null ? null : (totals[group.slug] ?? 0)}
            error={error}
            onRetry={retryLoading}
          />
        ))}
      </div>
      <GroupCompletionChart data={chartData} />
    </div>
  );
}
