"use client";

import { ChevronDown } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { WordMeanings } from "./word-meanings";
import type { SavedWord } from "@/lib/vocabulary-api";

export function WordTranslation({
  word,
  expanded,
  detailId,
  onToggle,
}: {
  word: SavedWord;
  expanded: boolean;
  detailId: string;
  onToggle: () => void;
}) {
  const previewRef = useRef<HTMLDivElement>(null);
  const [overflowing, setOverflowing] = useState(false);

  useLayoutEffect(() => {
    const preview = previewRef.current;
    if (!preview) return;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        setOverflowing(preview.scrollWidth > preview.clientWidth);
      });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(preview);
    measure();
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [word.meanings]);

  return (
    <div className="flex min-w-0 items-center gap-1">
      <div ref={previewRef} className="hidden min-w-0 flex-1 truncate sm:block">
        <WordMeanings meanings={word.meanings} inline />
      </div>
      <button
        type="button"
        className={`flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-sm text-emerald-700 focus-visible:outline-2 focus-visible:outline-emerald-700 sm:size-6 ${overflowing ? "" : "sm:invisible"}`}
        aria-label={`${expanded ? "收起" : "展开"} ${word.term} 的完整中文释义`}
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={onToggle}
      >
        <ChevronDown aria-hidden="true" className={`size-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>
    </div>
  );
}
