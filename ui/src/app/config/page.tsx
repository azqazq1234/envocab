"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { Header } from "@/components/layout/header";
import { UserManagement } from "@/components/config/user-management";

export default function ConfigPage() {
  const { user, loading } = useAuth();
  if (loading) return <main id="main-content" className="min-h-dvh" aria-busy="true" />;
  if (!user?.is_admin) {
    return (
      <main id="main-content" className="flex min-h-dvh items-center justify-center">
        <h1 className="text-6xl font-bold text-stone-400">404</h1>
      </main>
    );
  }
  return (
    <>
      <Header />
      <main id="main-content" className="mx-auto max-w-5xl px-5 pt-24 pb-10">
        <UserManagement />
      </main>
    </>
  );
}
