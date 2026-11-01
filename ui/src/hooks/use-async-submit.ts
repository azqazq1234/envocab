"use client";

import { useEffect, useRef, useState } from "react";

export function useAsyncSubmit(fallback: string) {
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => () => active.current?.abort(), []);

  async function run(
    action: (signal: AbortSignal) => void | Promise<void>,
    handleError?: (message: string) => boolean,
  ) {
    // The ref guards rapid clicks before React renders the busy state.
    if (active.current && !active.current.signal.aborted) return;
    const request = new AbortController();
    active.current = request;
    setBusy(true);
    setError("");
    try {
      await action(request.signal);
    } catch (cause) {
      if (!request.signal.aborted) {
        const message = cause instanceof Error ? cause.message : fallback;
        if (!handleError?.(message)) setError(message);
      }
    } finally {
      if (active.current === request) active.current = null;
      if (!request.signal.aborted) setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
