"use client";

import { useEffect, useRef, useState } from "react";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { useWordPronunciation } from "@/hooks/use-word-pronunciation";
import { useAuth } from "@/components/auth/auth-provider";
import { ArrowRight, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { WordMeanings } from "./word-meanings";
import { apiRequest, getRandomWord, type CheckResult, type SavedWord } from "@/lib/vocabulary-api";

export function VocabularyCheck({
  groupSlug,
  requestRevision,
}: {
  groupSlug: string;
  requestRevision: number;
}) {
  const { refreshProgress } = useAuth();
  const { busy: saving, error: saveError, setError: setSaveError, run } = useAsyncSubmit("Unable to save progress.");
  const activeLoad = useRef<AbortController | null>(null);
  const [result, setResult] = useState<(CheckResult & { key: string }) | null>(null);
  const [loadError, setLoadError] = useState("");
  const [revision, setRevision] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const previousId = useRef<number | null>(null);
  const fetching = useRef(true);
  const loadKey = `${groupSlug}:${revision}:${requestRevision}`;

  useEffect(() => {
    const request = new AbortController();
    activeLoad.current = request;
    fetching.current = true;

    async function loadWord() {
      const chosen = await getRandomWord(
        groupSlug,
        previousId.current,
        request.signal,
      );
      if (!request.signal.aborted) {
        previousId.current = chosen.word?.id ?? null;
        setLoadError("");
        setSaveError("");
        setResult({ ...chosen, key: loadKey });
        setRevealed(false);
        fetching.current = false;
      }
    }

    loadWord().catch((cause: unknown) => {
      if (!request.signal.aborted) {
        fetching.current = false;
        setResult(null);
        setLoadError(
          cause instanceof Error ? cause.message : "Unable to load vocabulary.",
        );
      }
    });
    return () => request.abort();
  }, [groupSlug, loadKey, setSaveError]);

  const nextDue = result?.key === loadKey && !result.word ? result.next_due : null;
  useEffect(() => {
    if (!nextDue) return;
    // Refresh when the next card is due; clean up when leaving this view.
    const timer = window.setTimeout(
      () => setRevision((value) => value + 1),
      Math.min(2_147_483_647, Math.max(1000, Date.parse(nextDue) - Date.now())),
    );
    return () => window.clearTimeout(timer);
  }, [nextDue]);

  function nextWord() {
    if (fetching.current) return;
    fetching.current = true;
    setLoadError("");
    setSaveError("");
    setResult(null);
    setRevealed(false);
    setRevision((value) => value + 1);
  }

  const word = result?.key === loadKey ? result.word : undefined;
  const error = loadError || saveError;
  const pronunciation = useWordPronunciation(
    word?.term,
    `${loadKey}:${word?.id ?? ""}`,
  );

  async function answer(value: "yes" | "not_sure" | "no") {
    if (!word || fetching.current) return;
    const wordRequest = activeLoad.current;
    await run(async (signal) => {
      await apiRequest<SavedWord>(`/words/${word.id}/progress`, {
        method: "POST",
        signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: value }),
      });
      if (signal.aborted) return;
      refreshProgress();
      // A late answer must not reveal a word loaded in the meantime.
      if (wordRequest?.signal.aborted) return;
      if (value === "yes") nextWord();
      else setRevealed(true);
    });
  }

  return (
    <div className="flex h-full min-h-0 items-center justify-center overflow-auto p-6 text-center">
      {error && !word ? (
        <div role="alert" className="text-muted-foreground">
          <p>{error}</p>
          <Button variant="link" className="cursor-pointer" onClick={nextWord}>
            Retry
          </Button>
        </div>
      ) : result === null ? null : word ? (
        <div className="grid h-full min-h-0 w-full max-w-3xl content-start grid-rows-[clamp(4rem,10vw,9rem)_2.5rem_clamp(6rem,16dvh,9rem)_6rem] gap-4 pt-[clamp(1rem,10dvh,6rem)]">
          <div className="flex min-h-0 items-center justify-center">
            <div className="relative flex min-h-0 max-h-full min-w-0 max-w-[calc(100%-7rem)] items-center sm:max-w-[calc(100%-8rem)]">
              <p
                lang="en"
                className="min-h-0 min-w-0 max-h-full max-w-full overflow-auto text-[clamp(3rem,8vw,7rem)] leading-tight font-bold text-emerald-700 [overflow-wrap:anywhere]"
              >
                {word.term}
              </p>
              <IconButton
                className="absolute inset-y-0 left-full my-auto ml-6 text-stone-500 active:not-aria-[haspopup]:translate-y-0 sm:ml-8"
                aria-label={`Play pronunciation of ${word.term}`}
                title="Play pronunciation (US)"
                onClick={pronunciation.replay}
              >
                <Volume2 aria-hidden="true" className="size-5" />
              </IconButton>
            </div>
          </div>
          <p lang="en" className="text-xl leading-relaxed text-stone-500 sm:text-2xl">
            {word.phonetic ? `[${word.phonetic}]` : null}
          </p>
          <div className="min-h-0 w-full overflow-y-auto" aria-live="polite">
            {pronunciation.message ? (
              <p role="status" className="mb-2 text-sm text-stone-500">{pronunciation.message}</p>
            ) : null}
            {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
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
                  disabled={saving}
                  onClick={() => void answer("no")}
                  title="Forgot or could not recall the meaning"
                >
                  NO
                </Button>
                <Button
                  className="h-11 min-w-24 cursor-pointer bg-[#e4b334] px-5 text-base text-white hover:bg-[#d3a224]"
                  disabled={saving}
                  onClick={() => void answer("not_sure")}
                  title="Recalled correctly, but with difficulty"
                >
                  HARD
                </Button>
                <Button
                  className="h-11 min-w-24 cursor-pointer bg-emerald-700 px-5 text-base text-white hover:bg-emerald-800"
                  disabled={saving}
                  onClick={() => void answer("yes")}
                  title="Recalled the meaning correctly"
                >
                  YES
                </Button>
              </>
            )}
          </div>
        </div>
      ) : result?.key === loadKey ? (
        <div className="space-y-3 text-muted-foreground" role="status">
          <p>{result.total === 0 ? "No words in this group." : "You're up to date. No words are due."}</p>
          {nextDue ? <p className="text-sm">Next review: {new Date(nextDue).toLocaleString()}</p> : null}
          {result.total > 0 ? (
            <Button variant="link" className="cursor-pointer" onClick={nextWord}>
              Check again
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
