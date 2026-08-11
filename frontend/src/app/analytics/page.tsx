"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type TrendPoint = {
  date: string;
  followers: number;
  reach: number;
  impressions: number;
  clicks: number;
  likes: number;
  comments: number;
  shares: number;
  leads: number;
  engagement_rate: number;
};

type PlatformRow = {
  platform: string;
  followers: number;
  reach: number;
  impressions: number;
  clicks: number;
  likes: number;
  comments: number;
  leads: number;
  engagement_rate: number;
};

type PostRow = {
  id: string;
  platform: string;
  title?: string | null;
  impressions: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  clicks: number;
  engagement_rate: number;
  measured_at: string;
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-ink/5 bg-white/85 p-4">
      <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">{label}</p>
      <p className="mt-2 font-display text-3xl tracking-tight">{value}</p>
    </div>
  );
}

export default function AnalyticsPage() {
  const { brandId, ready, user } = useAuth();
  const [days, setDays] = useState(30);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [platforms, setPlatforms] = useState<PlatformRow[]>([]);
  const [posts, setPosts] = useState<PostRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!brandId) return;
    const qs = `brand_id=${brandId}&days=${days}`;
    const [trendRows, platformRows, postRows] = await Promise.all([
      api<TrendPoint[]>(`/api/analytics/trends?${qs}`),
      api<PlatformRow[]>(`/api/analytics/platforms?brand_id=${brandId}`),
      api<PostRow[]>(`/api/analytics/posts?brand_id=${brandId}`),
    ]);
    setTrends(trendRows);
    setPlatforms(platformRows);
    setPosts(postRows);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId, days]);

  async function syncMetrics() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api<{ post_metrics: number; account_metrics: number }>(
        `/api/analytics/sync?days=${days}`,
        { method: "POST" },
      );
      setMessage(`Synced ${res.account_metrics} account days · ${res.post_metrics} posts`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  const latest = trends[trends.length - 1];
  const maxImpressions = Math.max(1, ...trends.map((t) => t.impressions));

  return (
    <AppShell title="Analytics" subtitle="Account, post and platform KPIs with trend comparisons">
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={() => void syncMetrics()}
          >
            Sync metrics
          </button>
          <select
            className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
          <p className="text-sm text-ink-mute">
            {trends.length ? `${trends.length} daily points` : "No metrics yet — sync to generate"}
          </p>
        </div>

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Followers" value={latest?.followers ?? 0} />
          <Stat label="Reach" value={latest?.reach ?? 0} />
          <Stat label="Impressions" value={latest?.impressions ?? 0} />
          <Stat label="Engagement rate" value={`${latest?.engagement_rate ?? 0}%`} />
          <Stat label="Clicks" value={latest?.clicks ?? 0} />
          <Stat label="Leads" value={latest?.leads ?? 0} />
          <Stat label="Likes (latest day)" value={latest?.likes ?? 0} />
          <Stat label="Comments (latest day)" value={latest?.comments ?? 0} />
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Impressions trend</h2>
          {trends.length === 0 ? (
            <p className="mt-3 text-sm text-ink-mute">No trend data yet.</p>
          ) : (
            <div className="mt-4 flex h-40 items-end gap-1">
              {trends.map((point) => (
                <div key={point.date} className="group relative flex-1">
                  <div
                    className="w-full rounded-t bg-tide/80 transition hover:bg-tide"
                    style={{ height: `${Math.max(6, (point.impressions / maxImpressions) * 100)}%` }}
                    title={`${point.date}: ${point.impressions} impressions`}
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">By platform</h2>
          <div className="mt-4 space-y-2">
            {platforms.length === 0 ? (
              <p className="text-sm text-ink-mute">No platform metrics yet.</p>
            ) : (
              platforms.map((row) => (
                <div
                  key={row.platform}
                  className="grid gap-2 rounded-xl border border-ink/5 bg-mist/40 px-4 py-3 text-sm md:grid-cols-5"
                >
                  <p className="font-medium capitalize">{row.platform}</p>
                  <p className="text-ink-mute">Followers {row.followers}</p>
                  <p className="text-ink-mute">Impressions {row.impressions}</p>
                  <p className="text-ink-mute">Clicks {row.clicks}</p>
                  <p className="text-ink-mute">ER {row.engagement_rate}%</p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Top posts</h2>
          <div className="mt-4 space-y-2">
            {posts.length === 0 ? (
              <p className="text-sm text-ink-mute">
                Publish content first, then sync metrics to see post performance.
              </p>
            ) : (
              posts.map((post) => (
                <div key={post.id} className="rounded-xl border border-ink/5 bg-mist/40 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">
                      {post.title || "Untitled"} · {post.platform}
                    </p>
                    <p className="text-xs text-ink-mute">ER {post.engagement_rate}%</p>
                  </div>
                  <p className="mt-1 text-xs text-ink-mute">
                    {post.impressions} impressions · {post.reach} reach · {post.likes} likes ·{" "}
                    {post.comments} comments · {post.clicks} clicks
                  </p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
