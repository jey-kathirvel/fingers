"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { api, type DashboardOverview } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-ink/5 bg-white/80 p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-ink-mute">{label}</p>
      <p className="mt-2 font-display text-3xl tracking-tight">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { orgId, ready, user } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !user || !orgId) return;
    api<DashboardOverview>("/api/analytics/overview")
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [ready, user, orgId]);

  return (
    <AppShell title="Dashboard" subtitle="What is happening, what needs attention, what to do next">
      {error ? <p className="text-red-700">{error}</p> : null}
      {!data ? (
        <p className="text-ink-mute">Loading live overview…</p>
      ) : (
        <div className="space-y-8">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Followers" value={data.followers} />
            <Stat label="Reach" value={data.reach} />
            <Stat label="Impressions" value={data.impressions} />
            <Stat label="Engagement rate" value={`${data.engagement_rate}%`} />
            <Stat label="Clicks" value={data.clicks} />
            <Stat label="Leads" value={data.leads} />
            <Stat label="Published posts" value={data.published_posts} />
            <Stat label="Drafts" value={data.draft_count ?? 0} />
            <Stat label="Approval items" value={data.approval_items} />
            <Stat label="Response backlog" value={data.response_backlog} />
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-ink/5 bg-white/80 p-5 lg:col-span-1">
              <h2 className="font-display text-2xl">Action queue</h2>
              <ul className="mt-4 space-y-3">
                {data.action_queue.map((item) => (
                  <li key={item.id} className="rounded-xl bg-mist px-3 py-3 text-sm">
                    <p className="font-medium">{item.title}</p>
                    <p className="text-ink-mute">
                      {item.type} · {item.priority}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-ink/5 bg-white/80 p-5">
              <h2 className="font-display text-2xl">Integration health</h2>
              <ul className="mt-4 space-y-3">
                {data.integration_health.map((item) => (
                  <li key={item.platform} className="flex items-center justify-between rounded-xl bg-mist px-3 py-3 text-sm">
                    <span className="capitalize">{item.platform}</span>
                    <span className="text-ink-mute">{item.status.replaceAll("_", " ")}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-ink-mute">
                Brands in workspace: <strong>{data.brands_count}</strong>
              </p>
            </div>
            <div className="rounded-2xl border border-ink/5 bg-white/80 p-5">
              <h2 className="font-display text-2xl">AI recommendations</h2>
              <ul className="mt-4 space-y-3">
                {data.recommendations.map((item) => (
                  <li key={item.id} className="rounded-xl bg-tide-soft/60 px-3 py-3 text-sm">
                    <p className="font-medium">{item.title}</p>
                    <p className="text-ink-mute">{item.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
