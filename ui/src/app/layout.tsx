import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";

export const metadata: Metadata = {
  title: "vocab",
  description: "English vocabulary learning",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Browser tools can inject attributes on <html> before React hydrates.
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full bg-stone-50 font-sans text-stone-900">
        <a
          href="#main-content"
          className="fixed left-4 top-2 z-50 -translate-y-24 rounded-md bg-emerald-700 px-4 py-2 text-sm text-white focus:translate-y-0"
        >
          Skip to main content
        </a>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
