"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const { login, context, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@ads-ai.in");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && context) {
    router.replace("/dashboard");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-forest/20 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-amber/20 blur-3xl" />
      </div>
      <div className="glass shadow-soft fade-up relative w-full max-w-md rounded-[2rem] p-8">
        <p className="text-xs uppercase tracking-[0.28em] text-forest">Fingers</p>
        <h1 className="display mt-3 text-4xl text-ink">Sign in</h1>
        <p className="fade-up-delay mt-2 text-sm text-ink/65">
          Multi-brand social control plane for plan → create → publish → engage.
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="mb-1.5 block text-ink/70">Email</span>
            <input
              className="w-full rounded-xl border border-[var(--line)] bg-white/80 px-3 py-2.5 outline-none ring-forest focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-ink/70">Password</span>
            <input
              className="w-full rounded-xl border border-[var(--line)] bg-white/80 px-3 py-2.5 outline-none ring-forest focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </label>
          {error ? (
            <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-forest px-4 py-3 text-sm font-semibold text-white transition hover:bg-forest-deep disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Enter workspace"}
          </button>
        </form>
      </div>
    </div>
  );
}
