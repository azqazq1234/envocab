"use client";

import { useEffect, useRef, useState } from "react";

export function useWordPronunciation(term: string | undefined, wordKey: string) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const replayRef = useRef<(() => void) | null>(null);
  const [issue, setIssue] = useState<{ key: string; message: string } | null>(null);

  useEffect(() => {
    if (!term) return;
    // Reuse the audio element after the user's first playback interaction.
    const audio = audioRef.current ?? new Audio();
    audioRef.current = audio;
    let active = true;
    let attempt = 0;
    const failed = () => {
      if (active) setIssue({ key: wordKey, message: "Audio unavailable. Click the speaker to retry." });
    };
    audio.src = `/api/pronunciation?${new URLSearchParams({ term })}`;
    audio.onplaying = () => {
      if (active) setIssue(null);
    };
    audio.onerror = failed;

    function play() {
      const currentAttempt = ++attempt;
      audio.currentTime = 0;
      void audio.play().catch((error: unknown) => {
        if (!active || currentAttempt !== attempt) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof DOMException && error.name === "NotAllowedError") return;
        failed();
      });
    }

    replayRef.current = () => {
      // Reload failed requests so a temporary network failure can be retried.
      if (audio.error) audio.load();
      play();
    };
    play();
    return () => {
      active = false;
      replayRef.current = null;
      audio.onplaying = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    };
  }, [term, wordKey]);

  return {
    replay: () => replayRef.current?.(),
    message: term && issue?.key === wordKey ? issue.message : "",
  };
}
