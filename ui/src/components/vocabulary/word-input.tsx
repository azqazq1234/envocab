"use client";

import {
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ComponentProps,
} from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

// Render beside the input inside its positioned parent so layout stays unchanged.
export function WordInput({
  ref,
  className,
  onFocus,
  onBlur,
  onSelect,
  onScroll,
  ...props
}: ComponentProps<typeof Input>) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const contextRef = useRef<CanvasRenderingContext2D | null>(null);
  useImperativeHandle(ref, () => inputRef.current!, []);
  const [caret, setCaret] = useState<{
    left: number;
    top: number;
    height: number;
  } | null>(null);

  function measureCaret() {
    const input = inputRef.current;
    if (
      !input ||
      document.activeElement !== input ||
      input.selectionStart !== input.selectionEnd
    ) {
      setCaret(null);
      return;
    }
    const context =
      contextRef.current ?? document.createElement("canvas").getContext("2d");
    if (!context) return;
    contextRef.current = context;
    const style = getComputedStyle(input);
    context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const textWidth = context.measureText(input.value).width;
    const prefixWidth = context.measureText(
      input.value.slice(0, input.selectionStart ?? 0),
    ).width;
    const metrics = context.measureText(input.value || "Ag");
    const height = Math.max(
      1,
      metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent,
    );
    const left =
      Math.max(0, (input.clientWidth - textWidth) / 2) +
      prefixWidth -
      input.scrollLeft;
    if (left < 0 || left > input.clientWidth) {
      setCaret(null);
      return;
    }
    setCaret({
      left: input.offsetLeft + Math.min(left, input.clientWidth - 3),
      top: input.offsetTop + (input.offsetHeight - height) / 2,
      height,
    });
  }

  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    const observer = new ResizeObserver(measureCaret);
    observer.observe(input);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <Input
        dir="ltr"
        lang="en"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="none"
        spellCheck={false}
        maxLength={100}
        {...props}
        ref={inputRef}
        className={cn(
          "h-16 border-0 px-0 text-center text-[40px] font-bold caret-transparent shadow-none focus-visible:border-transparent focus-visible:ring-0 aria-invalid:border-transparent aria-invalid:ring-0 md:text-[40px] dark:aria-invalid:ring-0",
          className,
        )}
        onFocus={(event) => {
          onFocus?.(event);
          measureCaret();
        }}
        onBlur={(event) => {
          onBlur?.(event);
          setCaret(null);
        }}
        onSelect={(event) => {
          onSelect?.(event);
          measureCaret();
        }}
        onScroll={(event) => {
          onScroll?.(event);
          measureCaret();
        }}
      />
      {caret ? (
        <span
          aria-hidden="true"
          className="word-input-caret pointer-events-none absolute z-10 w-[3px] bg-emerald-700"
          style={caret}
        />
      ) : null}
    </>
  );
}
