"use client";

import { useEffect, useRef, useState } from "react";

export function useAnimatedNumber(target: number) {
  const [value, setValue] = useState(0);
  const current = useRef(0);

  useEffect(() => {
    const startValue = current.current;
    if (startValue === target) return;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const started = performance.now();
    let frame: number;

    function update(now: number) {
      const progress = reducedMotion ? 1 : Math.min(1, (now - started) / 500);
      const eased = 1 - (1 - progress) ** 3;
      const next = progress === 1
        ? target
        : startValue + (target - startValue) * eased;
      current.current = next;
      setValue(next);
      if (progress < 1) frame = requestAnimationFrame(update);
    }

    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return value;
}
