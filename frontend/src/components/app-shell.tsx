"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/components/auth-provider";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/studio", label: "AI Studio" },
  { href: "/publishing", label: "Publishing" },
  { href: "/engagement", label: "Engagement" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/leads", label: "Leads" },
  { href: "/analytics", label: "Analytics" },
  { href: "/listening", label: "Listening" },
  { href: "/advisor", label: "AI Advisor" },
  { href: "/automations", label: "Automations" },
  { href: "/assets", label: "Assets" },
  { href: "/integrations", label: "Integrations" },
  { href: "/brands", label: "Brands" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle?: string }) {
  const { ready, user, memberships, brands, orgId, brandId, setOrgId, setBrandId, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="min-h-screen bg-atmosphere grid place-items-center text-ink-mute">
        Loading Fingers…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-atmosphere text-ink">
      <div className="mx-auto flex min-h-screen max-w-[1440px]">
        <aside className="hidden w-64 shrink-0 border-r border-ink/10 bg-white/70 p-5 backdrop-blur md:flex md:flex-col">
          <div className="mb-8">
            <p className="font-display text-3xl tracking-tight">fingers</p>
            <p className="text-xs uppercase tracking-[0.18em] text-ink-mute">Social Media Engineering</p>
          </div>
          <nav className="space-y-1 overflow-y-auto text-sm">
            {nav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-lg px-3 py-2 transition ${
                    active ? "bg-tide text-white" : "text-ink-soft hover:bg-mist-deep"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto pt-6 text-xs text-ink-mute">
            Phase 7 AI advisor
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-white/60 px-4 py-3 backdrop-blur md:px-8">
            <div>
              <h1 className="font-display text-2xl tracking-tight md:text-3xl">{title}</h1>
              {subtitle ? <p className="text-sm text-ink-mute">{subtitle}</p> : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
                value={orgId ?? ""}
                onChange={(e) => void setOrgId(e.target.value)}
              >
                {memberships.map((m) => (
                  <option key={m.organization_id} value={m.organization_id}>
                    {m.organization?.name || m.organization_id}
                  </option>
                ))}
              </select>
              <select
                className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
                value={brandId ?? ""}
                onChange={(e) => setBrandId(e.target.value)}
              >
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => void logout().then(() => router.push("/login"))}
                className="rounded-lg bg-ink px-3 py-2 text-sm text-white"
              >
                Log out
              </button>
            </div>
          </header>
          <main className="flex-1 p-4 md:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
