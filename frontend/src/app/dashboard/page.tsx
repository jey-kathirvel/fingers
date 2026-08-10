"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, type DashboardOverview } from "@/lib/utils";

export default function DashboardPage() {
  const { token, activeBrandId, context } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    const params = new URLSearchParams();
    if (context?.organization?.id) params.set("organization_id", context.organization.id);
    if (activeBrandId) params.set("brand_id", activeBrandId);
    apiFetch<DashboardOverview>(`/analytics/overview?${params}`, {}, token)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [token, activeBrandId, context?.organization?.id]);

  const kpis = data
    ? [
        ["Followers", data.followers],
        ["Reach", data.reach],
        ["Impressions", data.impressions],
        ["Engagement", `${data.engagement_rate}%`],
        ["Clicks", data.clicks],
        ["Leads", data.leads],
        ["Published", data.published_posts],
        ["Backlog", data.response_backlog],
      ]
    : [];

  return (
    <div className="space-y-4">
      <div className="glass shadow-soft fade-up overflow-hidden rounded-[2rem] p-6 md:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-forest">
              What needs attention
            </p>
            <h2 className="display mt-2 text-4xl text-ink md:text-5xl">
              Command center
            </h2>
            <p className="mt-3 max-w-2xl text-sm text-ink/65 md:text-base">
              Live Phase 1 dashboard backed by the FastAPI analytics overview.
              Social adapters arrive in later phases.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full bg-mist px-3 py-1.5 text-xs text-forest">
            <span className="pulse-dot inline-block h-2 w-2 rounded-full bg-forest" />
            API connected
          </div>
        </div>
      </div>

      {error ? (
        <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map(([label, value], idx) => (
          <div
            key={label as string}
            className="glass shadow-soft rounded-3xl p-5"
            style={{ animationDelay: `${idx * 40}ms` }}
          >
            <p className="text-xs uppercase tracking-[0.18em] text-ink/45">{label}</p>
            <p className="display mt-3 text-3xl text-ink">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass shadow-soft fade-up-delay rounded-[1.75rem] p-6">
          <h3 className="display text-2xl text-ink">Action queue</h3>
          <ul className="mt-4 space-y-3 text-sm text-ink/75">
            <li>Failed posts: {data?.failed_posts ?? "—"}</li>
            <li>Scheduled posts: {data?.scheduled_posts ?? "—"}</li>
            <li>Approval items: {data?.approval_items ?? "—"}</li>
            <li>Unanswered backlog: {data?.response_backlog ?? "—"}</li>
          </ul>
        </div>
        <div className="glass shadow-soft fade-up-delay rounded-[1.75rem] p-6">
          <h3 className="display text-2xl text-ink">AI recommendations</h3>
          <ul className="mt-4 space-y-3 text-sm text-ink/75">
            {(data?.ai_recommendations || []).map((item) => (
              <li key={item} className="border-l-2 border-forest/40 pl-3">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="glass shadow-soft rounded-[1.75rem] p-6">
        <h3 className="display text-2xl text-ink">Integration health</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {(data?.integration_health || []).map((item) => (
            <div key={item.platform} className="rounded-2xl bg-mist/70 px-4 py-3">
              <p className="font-medium text-ink">{item.platform}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-ink/50">
                {item.status.replaceAll("_", " ")}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
