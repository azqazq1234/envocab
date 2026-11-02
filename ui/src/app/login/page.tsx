import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <main id="main-content" tabIndex={-1} className="flex min-h-dvh items-center justify-center bg-[#fafaf9] px-5 py-12">
      <section aria-labelledby="login-title" className="flex aspect-square w-full max-w-sm items-stretch rounded-2xl bg-white p-6 shadow-[0_8px_16px_-8px_rgba(0,0,0,0.12),0_24px_56px_-16px_rgba(0,0,0,0.18)] sm:p-9">
        <LoginForm />
      </section>
    </main>
  );
}
