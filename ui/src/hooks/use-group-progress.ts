"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { apiRequest, type GroupSummary } from "@/lib/vocabulary-api";

export function useGroupProgress(revision = 0, includeAll = false) {
  const { progressRevision } = useAuth();
  const [groups, setGroups] = useState<GroupSummary[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const request = new AbortController();
    apiRequest<GroupSummary[]>(includeAll ? "/groups?include_all=true" : "/groups", { signal: request.signal, cache: "no-store" })
      .then((value) => {
        if (!request.signal.aborted) { setGroups(value); setError(false); }
      })
      .catch(() => {
        if (!request.signal.aborted) setError(true);
      });
    return () => request.abort();
  }, [progressRevision, revision, includeAll]);
  return { groups, error };
}
