"use client";

import { useRef, useState, type FormEvent } from "react";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { WordInput } from "@/components/vocabulary/word-input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { partOfSpeechLabels } from "@/lib/parts-of-speech";
import { apiRequest, type SavedWord } from "@/lib/vocabulary-api";

export type WordActionMode = "edit" | "delete";

type WordDialogProps = {
  word: SavedWord;
  mode: WordActionMode;
  groupSlug: string;
  groupLabel: string;
  onClose: () => void;
  onChanged: (id: number, deleted: boolean) => void;
};

export function WordDialog(props: WordDialogProps) {
  const { word, mode, groupSlug, groupLabel, onClose, onChanged } = props;
  if (mode === "delete") {
    return (
      <ConfirmationDialog
        title={`Delete word from ${groupLabel}`}
        confirmLabel="Delete"
        onClose={onClose}
        onConfirm={async (signal) => {
          await apiRequest(
            `/words/${word.id}?group=${encodeURIComponent(groupSlug)}`,
            { method: "DELETE", signal },
          );
          if (!signal.aborted) onChanged(word.id, true);
        }}
      >
        Confirm deletion of{" "}
        <strong className="font-bold text-foreground">{word.term}</strong>?
      </ConfirmationDialog>
    );
  }
  return <EditWordDialog word={word} onClose={onClose} onChanged={onChanged} />;
}

function EditWordDialog({
  word,
  onClose,
  onChanged,
}: Pick<WordDialogProps, "word" | "onClose" | "onChanged">) {
  const [term, setTerm] = useState(word.term);
  const [meanings, setMeanings] = useState(() =>
    word.meanings.map((meaning, id) => ({ ...meaning, id })),
  );
  const nextId = useRef(word.meanings.length);
  const { busy, error, setError, run } = useAsyncSubmit(
    "Unable to update word.",
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    return run(async (signal) => {
      await apiRequest(`/words/${word.id}`, {
        method: "PATCH",
        signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          term,
          phonetic:
            term.trim() === word.term ? word.phonetic : "",
          meanings: meanings.map(({ part_of_speech, meaning }) => ({
            part_of_speech,
            meaning,
          })),
        }),
      });
      if (signal.aborted) return;
      onClose();
      onChanged(word.id, false);
    });
  }

  return (
    <Dialog
      open
      onOpenChange={(value) => {
        if (!value && !busy) onClose();
      }}
    >
      <DialogContent className="flex h-128 flex-col overflow-hidden px-8 sm:max-w-lg">
        <DialogHeader className="sr-only">
          <DialogTitle>Edit word</DialogTitle>
          <DialogDescription>
            Changes to this word and its meanings apply to every group
            containing it.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col gap-4">
          <div className="relative mx-auto mt-6 mb-4 grid w-max min-w-[2px] max-w-full shrink-0 text-[40px] font-bold">
            <span aria-hidden="true" className="invisible h-16 whitespace-pre">
              {term || "\u200b"}
            </span>
            <WordInput
              id={`edit-word-${word.id}`}
              aria-label="English"
              className={`absolute inset-0 ${error ? "text-red-600" : "text-emerald-700"}`}
              aria-invalid={Boolean(error)}
              value={term}
              onChange={(event) => {
                setTerm(event.target.value);
                setError("");
              }}
              required
              disabled={busy}
            />
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 bottom-0 h-1 bg-emerald-700"
            />
          </div>
          <fieldset
            className="min-h-0 flex-1 space-y-3 overflow-y-auto"
            disabled={busy}
          >
            <legend className="mb-2 text-sm font-medium">Meanings</legend>
            {meanings.map((meaning, index) => (
              <div key={meaning.id} className="flex items-start gap-2">
                <select
                  aria-label={`Part of speech ${index + 1}`}
                  value={meaning.part_of_speech ?? ""}
                  onChange={(event) =>
                    setMeanings((rows) =>
                      rows.map((row) =>
                        row.id === meaning.id
                          ? {
                              ...row,
                              part_of_speech: event.target.value || null,
                            }
                          : row,
                      ),
                    )
                  }
                  className="h-8 w-16 shrink-0 cursor-pointer rounded-none border-0 border-b-2 border-emerald-700 bg-transparent px-1 text-sm outline-none focus-visible:border-emerald-700"
                >
                  <option value="">—</option>
                  {meaning.part_of_speech &&
                  !partOfSpeechLabels[meaning.part_of_speech] ? (
                    <option value={meaning.part_of_speech}>
                      {meaning.part_of_speech}
                    </option>
                  ) : null}
                  {Object.entries(partOfSpeechLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <Input
                  aria-label={`Chinese meaning ${index + 1}`}
                  lang="zh-CN"
                  className="min-w-0 rounded-none border-0 bg-transparent shadow-none focus-visible:border-transparent focus-visible:ring-0"
                  value={meaning.meaning}
                  onChange={(event) =>
                    setMeanings((rows) =>
                      rows.map((row) =>
                        row.id === meaning.id
                          ? { ...row, meaning: event.target.value }
                          : row,
                      ),
                    )
                  }
                  required
                  maxLength={10000}
                />
                <IconButton
                  className="text-red-600 hover:text-red-700"
                  disabled={meanings.length === 1}
                  aria-label={`Remove meaning ${index + 1}`}
                  onClick={() =>
                    setMeanings((rows) =>
                      rows.filter((row) => row.id !== meaning.id),
                    )
                  }
                >
                  <Trash2 aria-hidden="true" className="size-4" />
                </IconButton>
              </div>
            ))}
            <Button
              type="button"
              size="icon"
              aria-label="Add meaning"
              title="Add meaning"
              disabled={meanings.length >= 100}
              className="mx-auto flex size-11 cursor-pointer rounded-full bg-emerald-700 text-white shadow-md hover:bg-emerald-800"
              onClick={() => {
                const id = nextId.current++;
                setMeanings((rows) => [
                  ...rows,
                  {
                    id,
                    part_of_speech: null,
                    meaning: "",
                  },
                ]);
              }}
            >
              <Plus aria-hidden="true" className="size-5" />
            </Button>
          </fieldset>
          {error ? (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              type="submit"
              variant="link"
              disabled={
                busy ||
                !term.trim() ||
                meanings.some((meaning) => !meaning.meaning.trim())
              }
              className="cursor-pointer bg-transparent text-emerald-700 no-underline hover:text-emerald-800 hover:no-underline"
            >
              Save
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
