"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Bot,
  CalendarDays,
  Inbox,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Settings,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/studio", label: "AI Studio", icon: Sparkles },
  { href: "/dashboard/publishing", label: "Publishing", icon: CalendarDays },
  { href: "/dashboard/engagement", label: "Engagement", icon: Inbox },
  { href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/dashboard/leads", label: "Leads", icon: Users },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/advisor", label: "AI Advisor", icon: Bot },
  { href: "/dashboard/automations", label: "Automations", icon: Workflow },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { context, brands, activeBrandId, setActiveBrandId, logout, loading } =
    useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-forest">
        Loading Fingers…
      </div>
    );
  }

  if (!context) {
    router.replace("/login");
    return null;
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[1440px] gap-4 p-4 md:p-6">
      <aside className="glass shadow-soft hidden w-64 shrink-0 flex-col rounded-3xl p-5 md:flex">
        <div className="mb-8">
          <p className="text-xs uppercase tracking-[0.24em] text-forest/70">
            Social Media Engineering
          </p>
          <h1 className="display mt-2 text-3xl text-ink">Fingers</h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition",
                  active
                    ? "bg-forest text-white"
                    : "text-ink/75 hover:bg-mist hover:text-ink",
                )}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={() => logout().then(() => router.push("/login"))}
          className="mt-4 flex items-center gap-2 rounded-2xl px-3 py-2 text-sm text-ink/70 hover:bg-mist"
        >
          <LogOut size={16} />
          Log out
        </button>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="glass shadow-soft flex flex-wrap items-center justify-between gap-3 rounded-3xl px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-forest/70">
              {context.organization?.name || "Organization"}
            </p>
            <p className="mt-1 text-sm text-ink/70">
              Signed in as {context.user.full_name} · {context.role || "member"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs uppercase tracking-[0.16em] text-ink/50">
              Brand
            </label>
            <select
              className="rounded-xl border border-[var(--line)] bg-white/80 px-3 py-2 text-sm outline-none"
              value={activeBrandId || ""}
              onChange={(e) => setActiveBrandId(e.target.value)}
            >
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
          </div>
        </header>
        <section className="flex-1">{children}</section>
      </main>
    </div>
  );
}
