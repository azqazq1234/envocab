"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WordMeanings } from "./word-meanings";
import { getRandomWord, type SavedWord } from "@/lib/vocabulary-api";

export function VocabularyCheck({
  groupSlug,
  requestRevision,
  onTotalChange,
}: {
  groupSlug: string;
  requestRevision: number;
  onTotalChange: (total: number) => void;
}) {
  const [result, setResult] = useState<{ word: SavedWord | null } | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const previousId = useRef<number | null>(null);
  const fetching = useRef(true);

  useEffect(() => {
    const request = new AbortController();
    fetching.current = true;

    async function loadWord() {
      const chosen = await getRandomWord(
        groupSlug,
        previousId.current,
        request.signal,
      );
      if (!request.signal.aborted) {
        onTotalChange(chosen.total);
        previousId.current = chosen.word?.id ?? null;
        setResult({ word: chosen.word });
        setRevealed(false);
        fetching.current = false;
      }
    }

    loadWord().catch((cause: unknown) => {
      if (!request.signal.aborted) {
        fetching.current = false;
        setError(
          cause instanceof Error ? cause.message : "Unable to load vocabulary.",
        );
      }
    });
    return () => request.abort();
  }, [groupSlug, revision, requestRevision, onTotalChange]);

  function nextWord() {
    if (fetching.current) return;
    fetching.current = true;
    setError("");
    setRevision((value) => value + 1);
  }

  const word = result?.word;

  return (
    <div className="flex h-full min-h-0 items-center justify-center overflow-auto p-6 text-center">
      {error ? (
        <div role="alert" className="text-muted-foreground">
          <p>{error}</p>
          <Button variant="link" className="cursor-pointer" onClick={nextWord}>
            Retry
          </Button>
        </div>
      ) : result === null ? null : word ? (
        <div className="grid h-full min-h-0 w-full max-w-3xl content-start grid-rows-[clamp(4rem,10vw,9rem)_2.5rem_clamp(6rem,16dvh,9rem)_6rem] gap-4 pt-[clamp(1rem,10dvh,6rem)]">
          <p
            lang="en"
            className="min-h-0 max-w-full overflow-auto text-[clamp(3rem,8vw,7rem)] leading-tight font-bold text-emerald-700 [overflow-wrap:anywhere]"
          >
            {word.term}
          </p>
          <p
            lang="en"
            className="text-xl leading-relaxed text-stone-500 sm:text-2xl"
          >
            {revealed ? word.phonetic : null}
          </p>
          <div className="min-h-0 w-full overflow-y-auto" aria-live="polite">
            {revealed ? (
              <div className="flex flex-col gap-2 text-lg leading-relaxed text-stone-700">
                <WordMeanings meanings={word.meanings} />
              </div>
            ) : null}
          </div>
          <div className="flex h-24 items-start justify-center gap-3 pt-4 pb-6">
            {revealed ? (
              <button
                type="button"
                aria-label="Next word"
                title="Next word"
                className="inline-flex size-14 min-h-14 min-w-14 max-h-14 max-w-14 flex-none cursor-pointer items-center justify-center rounded-full bg-emerald-700 p-0 text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-700"
                onClick={nextWord}
              >
                <ArrowRight aria-hidden="true" className="size-7" />
              </button>
            ) : (
              <>
                <Button
                  className="h-11 min-w-24 cursor-pointer bg-red-700 px-5 text-base text-white hover:bg-red-800"
                  onClick={() => setRevealed(true)}
                >
                  NO
                </Button>
                <Button
                  className="h-11 min-w-24 cursor-pointer bg-[#e4b334] px-5 text-base text-white hover:bg-[#d3a224]"
                  onClick={() => setRevealed(true)}
                >
                  NOT SURE
                </Button>
                <Button
                  className="h-11 min-w-24 cursor-pointer bg-emerald-700 px-5 text-base text-white hover:bg-emerald-800"
                  onClick={nextWord}
                >
                  YES
                </Button>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
