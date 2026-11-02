import { invalidatePendingReads, sharedRead } from "./shared-read.ts";

export type WordMeaning = { part_of_speech: string | null; meaning: string };

type WordInput = {
  term: string;
  phonetic: string;
  meanings: WordMeaning[];
};

export type SavedWord = WordInput & {
  id: number;
  score: number;
  studied: boolean;
  groups: { slug: string; name: string }[];
  senior_type: "core" | "extend" | "basic" | null;
  senior_types: ("core" | "extend" | "basic")[];
};

export type DictionaryEntry = WordInput & { source: string };

export type WordPage = {
  items: SavedWord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type GroupSummary = {
  slug: string;
  name: string;
  total: number;
  studied: number;
  completion: number;
  score_counts: number[];
};

export function getRandomWord(
  group: string,
  excludeId: number | null,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ group });
  if (excludeId !== null) params.set("exclude_id", String(excludeId));
  return apiRequest<{ word: SavedWord | null; total: number }>(
    `/words/random?${params}`,
    { signal, cache: "no-store" },
  );
}

type WordPageOptions = {
  group: string;
  page?: number;
  pageSize?: number;
  sortBy?: "id" | "english" | "chinese";
  sortOrder?: "asc" | "desc";
  search?: string;
  locateId?: number;
  memberOf?: string[];
  seniorTypes?: string[];
};

export function getWordPage(options: WordPageOptions, signal?: AbortSignal) {
  const params = new URLSearchParams({ group: options.group });
  const fields = {
    page: options.page,
    page_size: options.pageSize,
    sort_by: options.sortBy,
    sort_order: options.sortOrder,
    q: options.search,
    locate_id: options.locateId,
    member_of: options.memberOf?.length ? options.memberOf.join(",") : undefined,
    senior_types: options.seniorTypes?.length ? options.seniorTypes.join(",") : undefined,
  };
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined) params.set(key, String(value));
  }
  return apiRequest<WordPage>(`/words?${params}`, { signal });
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  fallback = "Unable to load or save vocabulary. Please try again.",
): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  if (method === "GET") {
    const { signal, ...options } = init ?? {};
    const headers = [...new Headers(options.headers).entries()].sort();
    const requestOptions = Object.entries({ ...options, method, headers }).sort(
      ([left], [right]) => left.localeCompare(right),
    );
    const key = JSON.stringify([path, requestOptions, fallback]);
    return sharedRead<T>(
      key,
      (sharedSignal) =>
        fetchJson<T>(path, { ...options, signal: sharedSignal }, fallback),
      signal,
    );
  }
  invalidatePendingReads();
  try {
    return await fetchJson<T>(path, init, fallback);
  } finally {
    invalidatePendingReads();
  }
}

async function fetchJson<T>(
  path: string,
  init: RequestInit | undefined,
  fallback: string,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if ((init?.method ?? "GET").toUpperCase() !== "GET") headers.set("X-Envocab-Request", "1");
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("envocab-session-expired"));
    }
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((error: { msg?: string }) => error.msg)
              .filter(Boolean)
              .join("; ")
          : "";
    throw new Error(message || fallback);
  }
  if (data === null)
    throw new Error("Server returned an invalid response. Please try again.");
  return data as T;
}
