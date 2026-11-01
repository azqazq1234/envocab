import Link from "next/link";
import { BookOpen } from "lucide-react";

export function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center bg-background shadow-[0_3px_12px_-4px_rgba(0,0,0,0.15)]">
      <Link
        href="/"
        aria-label="Envocab home"
        className="flex w-16 shrink-0 items-center justify-center rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-700"
      >
        <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-700 text-white">
          <BookOpen aria-hidden="true" className="size-5" />
        </span>
      </Link>
      <span className="text-lg font-semibold tracking-widest text-emerald-700">
        VOCAB
      </span>
    </header>
  );
}
