"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";
import { useAuth } from "./auth-provider";
import { useAsyncSubmit } from "@/hooks/use-async-submit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginForm() {
  const router = useRouter();
  const { user, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const { busy, error, setError, run } = useAsyncSubmit("Unable to log in. Please try again.");

  useEffect(() => {
    if (!loading && user) router.replace("/all");
  }, [loading, user, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || user) return;
    const normalized = username.normalize("NFKC").trim().toLowerCase();
    if (!/^[a-z0-9_-]{1,40}$/.test(normalized)) return;
    await run((signal) => login(normalized, signal));
  }

  const pending = loading || busy || Boolean(user);

  return (
    <div lang="en" className="flex min-h-0 w-full flex-col overflow-y-auto">
      <div className="mb-10 flex items-center gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-emerald-700 text-white">
          <BookOpen aria-hidden="true" className="size-6" />
        </span>
        <p className="text-xl font-semibold tracking-widest text-emerald-700">VOCAB</p>
      </div>
      <h1 id="login-title" className="text-2xl font-semibold tracking-tight text-stone-900">LOGIN</h1>
      <form onSubmit={submit} noValidate className="mt-7 flex min-h-0 flex-1 flex-col" aria-busy={pending}>
        <label htmlFor="login-username" className="sr-only">Username</label>
        <Input
          id="login-username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="Enter your username"
          value={username}
          onChange={(event) => { setUsername(event.target.value); setError(""); }}
          disabled={pending}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "login-error" : undefined}
          className="h-11 shrink-0 rounded-lg border-stone-200 bg-stone-50 px-3 text-sm focus-visible:border-emerald-700 focus-visible:ring-0 focus-visible:shadow-none"
        />
        {error ? <p id="login-error" role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
        <Button type="submit" className="mt-auto h-11 w-full shrink-0 cursor-pointer rounded-lg bg-emerald-700 text-sm font-medium text-white hover:bg-emerald-800">
          LOG IN
        </Button>
      </form>
    </div>
  );
}
