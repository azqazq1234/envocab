import { apiRequest, type DictionaryEntry } from "./vocabulary-api.ts";

export type LookupState = {
  entry: DictionaryEntry | null;
  error: string;
  loading: boolean;
  duplicate: boolean;
};

const emptyState: LookupState = {
  entry: null,
  error: "",
  loading: false,
  duplicate: false,
};
const DEBOUNCE_MS = 500;
const SINGLE_LETTER_DEBOUNCE_MS = 1500;
const MIN_INTERVAL_MS = 800;

async function fetchEntry(
  word: string,
  signal: AbortSignal,
): Promise<DictionaryEntry> {
  return apiRequest<DictionaryEntry>(
    `/dictionary/lookup?term=${encodeURIComponent(word)}`,
    { signal },
    "Lookup failed. Please try again.",
  );
}

export async function checkWordAvailability(
  group: string,
  word: string,
  signal: AbortSignal,
): Promise<boolean> {
  const result = await apiRequest<{ exists: boolean }>(
    `/words/exists?group=${encodeURIComponent(group)}&term=${encodeURIComponent(word)}`,
    { signal, cache: "no-store" },
    "Unable to check existing words. Please try again.",
  );
  return !result.exists;
}

export function createDictionaryLookup(
  onChange: (state: LookupState) => void,
  lookup: (
    word: string,
    signal: AbortSignal,
  ) => Promise<DictionaryEntry> = fetchEntry,
  checkAvailability?: (word: string, signal: AbortSignal) => Promise<boolean>,
) {
  let pending: ReturnType<typeof setTimeout> | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let active: AbortController | undefined;
  let generation = 0;
  let lastStarted = -Infinity;
  const cache = new Map<string, DictionaryEntry>();

  function cancel() {
    generation += 1;
    clearTimeout(pending);
    clearTimeout(timeout);
    active?.abort();
    active = undefined;
  }

  function reset() {
    cancel();
    onChange(emptyState);
  }

  function search(input: string) {
    reset();
    const word = input.trim();
    if (
      word.length > 100 ||
      !/^[A-Za-z][A-Za-z .'/\-]*$/.test(word)
    )
      return;
    const cached = cache.get(word);
    if (cached && !checkAvailability) {
      onChange({ entry: cached, error: "", loading: false, duplicate: false });
      return;
    }
    const current = generation;
    const delay = Math.max(
      (word.match(/[A-Za-z]/g)?.length ?? 0) === 1
        ? SINGLE_LETTER_DEBOUNCE_MS
        : DEBOUNCE_MS,
      MIN_INTERVAL_MS - (Date.now() - lastStarted),
    );
    pending = setTimeout(() => {
      pending = undefined;
      const request = new AbortController();
      active = request;
      lastStarted = Date.now();
      onChange({ entry: null, error: "", loading: true, duplicate: false });
      const requestTimeout = setTimeout(() => request.abort(), 15000);
      timeout = requestTimeout;
      Promise.all([
        checkAvailability
          ? checkAvailability(word, request.signal)
          : Promise.resolve(true),
        cached ? Promise.resolve(cached) : lookup(word, request.signal),
      ])
        .then(([available, entry]) => {
          if (generation !== current || request.signal.aborted) return;
          if (cache.size >= 50) cache.delete(cache.keys().next().value!);
          cache.set(word, entry);
          onChange({ entry, error: "", loading: false, duplicate: !available });
        })
        .catch((cause: unknown) => {
          if (generation !== current) return;
          onChange({
            entry: null,
            error: request.signal.aborted
              ? "Lookup timed out. Please try again."
              : cause instanceof Error
                ? cause.message
                : "Lookup failed. Please try again.",
            loading: false,
            duplicate: false,
          });
        })
        .finally(() => {
          clearTimeout(requestTimeout);
          if (generation === current) active = undefined;
        });
    }, delay);
  }

  return { search, reset, dispose: cancel };
}
