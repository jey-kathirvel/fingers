"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function HomePage() {
  const router = useRouter();
  const { context, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    router.replace(context ? "/dashboard" : "/login");
  }, [context, loading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="fade-up text-center">
        <p className="text-xs uppercase tracking-[0.28em] text-forest">Fingers</p>
        <h1 className="display mt-3 text-4xl text-ink">Preparing workspace…</h1>
      </div>
    </div>
  );
}
