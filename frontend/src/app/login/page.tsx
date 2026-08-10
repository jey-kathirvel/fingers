"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const { ready, user, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@fingers.ads-ai.in");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-atmosphere px-4 py-10">
      <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1.1fr_0.9fr] md:items-center">
        <section className="text-ink">
          <p className="mb-3 text-xs uppercase tracking-[0.22em] text-tide">fingers.ads-ai.in</p>
          <h1 className="font-display text-5xl leading-[1.05] tracking-tight md:text-6xl">
            Social Media Engineering & Engagement
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-mute">
            Plan → Create → Approve → Publish → Engage → Analyze from one multi-brand control plane.
          </p>
        </section>

        <form onSubmit={onSubmit} className="rounded-2xl bg-white/80 p-6 shadow-panel backdrop-blur">
          <h2 className="font-display text-3xl">Sign in</h2>
          <p className="mt-1 text-sm text-ink-mute">Access your organization workspace</p>
          <label className="mt-6 block text-sm">
            Email
            <input
              className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="mt-4 block text-sm">
            Password
            <input
              className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
          <button
            disabled={loading}
            className="mt-6 w-full rounded-lg bg-tide px-4 py-3 font-medium text-white disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Enter Fingers"}
          </button>
        </form>
      </div>
    </div>
  );
}
