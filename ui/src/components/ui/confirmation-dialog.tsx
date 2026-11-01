"use client";

import type { ReactNode } from "react";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function ConfirmationDialog({
  title,
  children,
  confirmLabel,
  onConfirm,
  onClose,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  onConfirm: (signal: AbortSignal) => void | Promise<void>;
  onClose: () => void;
}) {
  const { busy, error, run } = useAsyncSubmit(
    "Unable to complete this action.",
  );

  function confirm() {
    return run(async (signal) => {
      await onConfirm(signal);
      if (!signal.aborted) onClose();
    });
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <DialogContent className="h-56 max-h-[calc(100dvh-2rem)] grid-rows-[1fr_auto_1fr] gap-0 overflow-y-auto sm:max-w-lg">
        <DialogHeader className="row-start-2 text-center">
          <DialogTitle className="sr-only">{title}</DialogTitle>
          <DialogDescription className="text-lg">{children}</DialogDescription>
        </DialogHeader>
        <form
          className="row-start-3 space-y-4 self-end"
          onSubmit={(event) => {
            event.preventDefault();
            void confirm();
          }}
        >
          {error ? (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          ) : null}
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="link"
              disabled={busy}
              className="cursor-pointer bg-transparent text-red-600 no-underline hover:text-red-700 hover:no-underline"
            >
              {confirmLabel}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
