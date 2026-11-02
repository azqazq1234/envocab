"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/vocabulary-api";

export type User = { id: number; username: string; is_admin: boolean };

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (username: string, signal?: AbortSignal) => Promise<void>;
  logout: (signal?: AbortSignal) => Promise<void>;
  deleteAccount: (signal?: AbortSignal) => Promise<void>;
  progressRevision: number;
  refreshProgress: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [progressRevision, setProgressRevision] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    const expire = () => setUser(null);
    window.addEventListener("envocab-session-expired", expire);
    apiRequest<User | null>("/auth/me", { signal: request.signal, cache: "no-store" })
      .then((value) => {
        if (!request.signal.aborted) setUser(value);
      })
      .catch(() => {
        if (!request.signal.aborted) setUser(null);
      })
      .finally(() => {
        if (!request.signal.aborted) setLoading(false);
      });
    return () => {
      request.abort();
      window.removeEventListener("envocab-session-expired", expire);
    };
  }, []);

  async function login(username: string, signal?: AbortSignal) {
    const value = await apiRequest<User>("/auth/login", {
      method: "POST",
      signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
    setUser(value);
  }

  async function logout(signal?: AbortSignal) {
    await apiRequest<void>("/auth/logout", { method: "POST", signal });
    setUser(null);
  }

  async function deleteAccount(signal?: AbortSignal) {
    await apiRequest<void>("/auth/me", { method: "DELETE", signal });
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, deleteAccount, progressRevision, refreshProgress: () => setProgressRevision((value) => value + 1) }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth requires AuthProvider");
  return context;
}

export function AccountContent({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main id="main-content" className="flex min-h-dvh items-center justify-center bg-[#fafaf9]">
        <p role="status" className="text-sm text-stone-500">
          {loading ? "加载中…" : "正在进入登录页…"}
        </p>
      </main>
    );
  }
  // Discard pending requests, selections and dialogs when the account changes.
  return <div key={user.id}>{children}</div>;
}
