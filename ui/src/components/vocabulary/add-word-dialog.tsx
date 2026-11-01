"use client";

import { useEffect, useRef, useState } from "react";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { ArrowRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WordInput } from "@/components/vocabulary/word-input";
import { apiRequest } from "@/lib/vocabulary-api";
import {
  createDictionaryLookup,
  checkWordAvailability,
  type LookupState,
} from "@/lib/dictionary-lookup";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function AddWordDialog({
  groupLabel,
  groupSlug,
  onAdded,
}: {
  groupLabel: string;
  groupSlug: string;
  onAdded: () => void;
}) {
  const [open, setOpen] = useState(false);
  const {
    busy: saving,
    error: saveError,
    setError: setSaveError,
    run,
  } = useAsyncSubmit("Unable to save word.");
  const inputRef = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState("");
  const [{ entry, error, loading, duplicate }, setLookupState] =
    useState<LookupState>({
      entry: null,
      error: "",
      loading: false,
      duplicate: false,
    });
  const lookup = useRef<ReturnType<typeof createDictionaryLookup> | null>(null);
  const hasError = Boolean(error || saveError);
  const visibleError =
    saveError ||
    (error === "No dictionary entry found for this word." ? "" : error);

  useEffect(() => {
    const controller = createDictionaryLookup(
      setLookupState,
      undefined,
      (word, signal) => checkWordAvailability(groupSlug, word, signal),
    );
    lookup.current = controller;
    return () => {
      controller.dispose();
      lookup.current = null;
    };
  }, [groupSlug]);

  useEffect(() => {
    if (open && !saving) inputRef.current?.focus();
  }, [open, saving]);

  function saveWord() {
    if (!entry || loading || duplicate) return;
    return run(
      async (signal) => {
        await apiRequest(`/groups/${encodeURIComponent(groupSlug)}/words`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            term: entry.term,
            phonetic: entry.phonetic,
            meanings: entry.meanings,
          }),
          signal,
        });
        if (signal.aborted) return;
        lookup.current?.reset();
        setTerm("");
        onAdded();
      },
      (message) => {
        if (message !== "This word already exists in this group.") return false;
        lookup.current?.reset();
        setLookupState({ entry, error: "", loading: false, duplicate: true });
        return true;
      },
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (saving) return;
        setOpen(nextOpen);
        setSaveError("");
        lookup.current?.reset();
        setTerm("");
      }}
    >
      <DialogTrigger
        render={
          <Button
            size="icon"
            className="size-9 cursor-pointer rounded-full bg-emerald-700 text-white shadow-md hover:bg-emerald-800"
          />
        }
        aria-label={`Add word to ${groupLabel}`}
        title="Add word"
      >
        <Plus aria-hidden="true" className="size-4" />
      </DialogTrigger>
      <DialogContent
        aria-describedby={undefined}
        className="flex h-128 flex-col gap-1 overflow-hidden px-8 sm:max-w-lg"
      >
        <DialogTitle className="sr-only">Add word</DialogTitle>
        <div className="relative mx-auto mt-6 w-full max-w-full shrink-0">
          {term.length === 0 ? (
            <ArrowRight
              aria-hidden="true"
              strokeWidth={1}
              className="pointer-events-none absolute right-1/2 top-1/2 mr-3 size-10 -translate-y-1/2 text-emerald-700"
            />
          ) : null}
          <WordInput
            ref={inputRef}
            id="lookup-word"
            name="word"
            aria-label="Word"
            style={{ boxShadow: "none", backgroundColor: "transparent" }}
            value={term}
            onChange={(event) => {
              setSaveError("");
              setTerm(event.target.value);
              lookup.current?.search(event.target.value);
            }}
            onKeyDown={(event) => {
              if (
                event.key !== "Enter" ||
                event.nativeEvent.isComposing ||
                event.nativeEvent.keyCode === 229
              )
                return;
              event.preventDefault();
              if (!event.repeat) void saveWord();
            }}
            disabled={saving}
            className={`${hasError ? "text-red-600" : "text-emerald-700"}`}
            aria-invalid={hasError}
            aria-describedby={visibleError ? "lookup-error" : undefined}
          />
        </div>
        {visibleError ? (
          <p id="lookup-error" role="alert" className="text-sm text-red-600">
            {visibleError}
          </p>
        ) : null}
        <div
          aria-live="polite"
          aria-busy={loading}
          className="min-h-0 overflow-y-auto"
        >
          {entry ? (
            <div className="space-y-5 border-t pt-4">
              <div className="flex flex-wrap items-baseline gap-3">
                <h2 className="text-xl font-semibold">{entry.term}</h2>
                {entry.phonetic ? (
                  <span className="text-sm text-muted-foreground">
                    /{entry.phonetic}/
                  </span>
                ) : null}
              </div>
              <ul className="space-y-4">
                {entry.meanings.map((meaning, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="min-w-20 shrink-0 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                      {meaning.part_of_speech ?? "Unspecified"}
                    </span>
                    <p
                      lang="zh-CN"
                      className="min-w-0 break-words text-sm leading-6"
                    >
                      {meaning.meaning}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <div className="mt-auto flex shrink-0 justify-end">
          <Button
            type="button"
            size="icon"
            aria-label="ADD"
            title="ADD"
            disabled={!entry || loading || saving || duplicate}
            onClick={saveWord}
            className={`size-11 cursor-pointer rounded-full text-white shadow-md ${duplicate ? "bg-amber-400" : "bg-emerald-700 hover:bg-emerald-800"}`}
          >
            <Plus aria-hidden="true" className="size-5" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
