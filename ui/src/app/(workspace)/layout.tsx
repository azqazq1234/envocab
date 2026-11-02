import type { ReactNode } from "react";
import { AccountContent } from "@/components/auth/auth-provider";
import { Header } from "@/components/layout/header";
import { AppShell } from "@/components/layout/app-shell";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <AccountContent>
      <Header className="hidden sm:flex" />
      <AppShell>{children}</AppShell>
    </AccountContent>
  );
}
