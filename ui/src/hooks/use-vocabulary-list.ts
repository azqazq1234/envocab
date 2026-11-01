"use client";

import { useEffect, useRef, useState, useLayoutEffect } from "react";
import { fittingPageSize } from "@/lib/vocabulary-layout";
import { getWordPage, type WordPage } from "@/lib/vocabulary-api";

export type WordFocusTarget = { id: number; revision: number } | null;

// The API clamps an oversized page to the last available page.
const LAST_PAGE = Number.MAX_SAFE_INTEGER;

export function useVocabularyList({
  groupSlug,
  additionRevision,
  focusTarget,
  onTotalChange,
  memberOf,
  seniorTypes,
}: {
  groupSlug: string;
  additionRevision: number;
  focusTarget: WordFocusTarget;
  onTotalChange: (total: number) => void;
  memberOf?: string[];
  seniorTypes?: string[];
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const highlightedTarget = useRef<WordFocusTarget>(null);
  const locatedTarget = useRef<WordFocusTarget>(null);
  const membershipKey = `${memberOf?.join(",") ?? ""}|${seniorTypes?.join(",") ?? ""}`;
  const [navigation, setNavigation] = useState(() => ({
    page: additionRevision > 0 ? LAST_PAGE : 1,
    additionRevision,
    membershipKey,
  }));
  const page =
    navigation.membershipKey !== membershipKey
      ? 1
      : navigation.additionRevision === additionRevision
        ? navigation.page
        : LAST_PAGE;
  const [automaticPageSize, setAutomaticPageSize] = useState<number | null>(null);
  const [manualPageSize, setManualPageSize] = useState<number | null>(null);
  const measuring = manualPageSize === null && automaticPageSize === null;
  const pageSize = manualPageSize ?? automaticPageSize ?? 10;
  const [retry, setRetry] = useState(0);
  const [sort, setSort] = useState<"asc" | "desc" | null>(null);
  const sortBy = sort === null ? "id" : "english";
  const sortOrder = sort ?? "asc";
  const keyPrefix = `${groupSlug}:${membershipKey}:${pageSize}:${retry}:${additionRevision}:${sortBy}:${sortOrder}:${focusTarget?.id ?? 0}:${focusTarget?.revision ?? 0}`;
  const key = `${keyPrefix}:${page}`;
  const [result, setResult] = useState<{
    key: string;
    data: WordPage | null;
    error: string;
  }>({ key: "", data: null, error: "" });

  useEffect(() => {
    if (measuring) return;
    if (result.key === key) return;
    const request = new AbortController();
    const locating =
      focusTarget !== null && locatedTarget.current !== focusTarget;
    getWordPage(
      {
        group: groupSlug,
        memberOf,
        seniorTypes,
        page,
        pageSize,
        sortBy,
        sortOrder,
        locateId: locating ? focusTarget.id : undefined,
      },
      request.signal,
    )
      .then((data) => {
        if (!request.signal.aborted) {
          if (locating) {
            locatedTarget.current = focusTarget;
          }
          setNavigation({ page: data.page, additionRevision, membershipKey });
          setResult({ key: `${keyPrefix}:${data.page}`, data, error: "" });
          onTotalChange(data.total);
        }
      })
      .catch((cause: unknown) => {
        if (!request.signal.aborted)
          setResult({
            key,
            data: null,
            error:
              cause instanceof Error
                ? cause.message
                : "Unable to load vocabulary.",
          });
      });
    return () => request.abort();
  }, [
    groupSlug,
    memberOf,
    seniorTypes,
    membershipKey,
    page,
    pageSize,
    measuring,
    key,
    keyPrefix,
    sortBy,
    sortOrder,
    onTotalChange,
    focusTarget,
    additionRevision,
    result.key,
  ]);

  const loading = result.key !== key;
  const words = result.data?.items ?? [];
  const empty = Boolean(result.error) || words.length === 0;
  const currentPage = result.data?.page ?? 1;
  const totalPages = result.data?.total_pages ?? 1;

  useLayoutEffect(() => {
    const container = scrollRef.current;
    const table = container?.querySelector("table");
    const header = table?.querySelector("thead");
    if (!container || !table || !header) return;
    const contents = Array.from(
      table.querySelectorAll<HTMLElement>("[data-chinese-content]"),
    );
    const rows = Array.from(table.querySelectorAll("tbody tr[data-word-id]"));
    const probe = table.querySelector("[data-page-size-probe]");
    let frame = 0;

    const measureActionsShadow = () => {
      const viewport = container.parentElement;
      const actions = header.querySelector("th:last-child");
      if (!viewport || !actions) return;
      const bounds = actions.getBoundingClientRect();
      // Share the actual scrollbar/sticky-column inset with the footer so its
      // page-size text starts at the same padding as the Actions heading.
      const list = viewport.parentElement;
      list?.style.setProperty(
        "--actions-column-right",
        `${Math.max(0, list.getBoundingClientRect().right - bounds.right)}px`,
      );
      viewport.style.setProperty(
        "--actions-shadow-height",
        `${Math.max(0, table.getBoundingClientRect().height - container.scrollTop)}px`,
      );
      viewport.style.setProperty("--actions-shadow-width", `${bounds.width}px`);
      viewport.style.setProperty(
        "--actions-shadow-right",
        `${viewport.getBoundingClientRect().right - bounds.right}px`,
      );
    };

    const measureWidth = () => {
      const chineseWidth = Math.max(
        0,
        ...contents.map((content) => {
          const style = getComputedStyle(content.parentElement!);
          return (
            content.getBoundingClientRect().width +
            parseFloat(style.paddingLeft) +
            parseFloat(style.paddingRight)
          );
        }),
      );
      table.style.setProperty(
        "--chinese-content-width",
        `${Math.ceil(chineseWidth)}px`,
      );
    };

    const measure = () => {
      measureWidth();
      measureActionsShadow();
      if (manualPageSize !== null) return;
      const sizingRows = rows.length ? rows : probe ? [probe] : [];
      if (sizingRows.length === 0) return;
      const rowHeight = Math.max(
        ...sizingRows.map((row) => row.getBoundingClientRect().height),
      );
      if (container.clientHeight <= 0 || rowHeight <= 0) return;
      const size = fittingPageSize(
        container.clientHeight,
        header.getBoundingClientRect().height,
        rowHeight,
      );
      if (size === automaticPageSize) return;
      container.scrollTo({ top: 0 });
      setAutomaticPageSize(size);
      // Initial sizing must preserve pending last-page/search navigation.
      if (automaticPageSize === null) return;
      setNavigation({
        page: Math.floor(((currentPage - 1) * pageSize) / size) + 1,
        additionRevision,
        membershipKey,
      });
    };

    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    });
    // Tabs can briefly lay out both panels during their layout effects. Measure
    // pagination on the next frame, after the inactive panel has been hidden.
    measureWidth();
    measureActionsShadow();
    frame = requestAnimationFrame(measure);
    container.addEventListener("scroll", measureActionsShadow, { passive: true });
    [container, table, header, ...contents, ...rows, ...(probe ? [probe] : [])].forEach((node) =>
      observer.observe(node),
    );
    return () => {
      container.removeEventListener("scroll", measureActionsShadow);
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [result.data, manualPageSize, automaticPageSize, pageSize, currentPage, additionRevision, membershipKey]);

  useEffect(() => {
    if (loading || !focusTarget || highlightedTarget.current === focusTarget)
      return;
    const container = scrollRef.current;
    const row = container?.querySelector<HTMLElement>(
      `[data-word-id="${focusTarget.id}"]`,
    );
    if (!container || !row) return;
    const frame = requestAnimationFrame(() => {
      if (row.getBoundingClientRect().height === 0) return;
      highlightedTarget.current = focusTarget;
      const bounds = container.getBoundingClientRect();
      const rowBounds = row.getBoundingClientRect();
      container.scrollTo({
        top:
          container.scrollTop +
          rowBounds.top -
          bounds.top -
          (container.clientHeight - rowBounds.height) / 2,
      });
      row.focus({ preventScroll: true });
      row.querySelectorAll("td").forEach((cell) => {
        const original = getComputedStyle(cell).backgroundColor;
        cell.animate(
          [
            { backgroundColor: original },
            { backgroundColor: "#ecfdf5" },
            { backgroundColor: original },
          ],
          { duration: 650, iterations: 2, easing: "ease-in-out" },
        );
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [loading, focusTarget, result.data]);

  function navigateToPage(page: number) {
    scrollRef.current?.scrollTo({ top: 0 });
    setNavigation({ page, additionRevision, membershipKey });
  }

  function changeSort(order: "asc" | "desc" | null) {
    setSort(order);
    navigateToPage(1);
  }

  function changePageSize(size: number) {
    setManualPageSize(size);
    navigateToPage(1);
  }

  return {
    scrollRef,
    data: result.data,
    error: result.error,
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
    refresh: () => setRetry((value) => value + 1),
  };
}
