"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type Campaign = {
  id: string;
  name: string;
  objective?: string | null;
  platforms?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  kpi_targets?: string | null;
  notes?: string | null;
  content_item_ids: string[];
};

type ContentItem = {
  id: string;
  title: string;
  status: string;
};

const STATUSES = ["draft", "active", "paused", "completed"];

export default function CampaignsPage() {
  const { brandId, ready, user } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("awareness");
  const [platforms, setPlatforms] = useState("linkedin,instagram,facebook");
  const [kpiTargets, setKpiTargets] = useState("Reach + engagement lift");
  const [contentId, setContentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = campaigns.find((c) => c.id === selectedId) || null;

  async function refresh() {
    if (!brandId) return;
    const [camp, content] = await Promise.all([
      api<Campaign[]>(`/api/campaigns?brand_id=${brandId}`),
      api<ContentItem[]>(`/api/content?brand_id=${brandId}`),
    ]);
    setCampaigns(camp);
    setContents(content);
    if (!selectedId && camp[0]) setSelectedId(camp[0].id);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load campaigns");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!brandId || !name.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const created = await api<Campaign>("/api/campaigns", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          name: name.trim(),
          objective,
          platforms: platforms.split(",").map((p) => p.trim()).filter(Boolean),
          status: "draft",
          kpi_targets: kpiTargets,
        }),
      });
      setName("");
      setMessage("Campaign created");
      await refresh();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(status: string) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/api/campaigns/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setMessage(`Campaign marked ${status}`);
      await refresh();
      setSelectedId(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function linkContent() {
    if (!selected || !contentId) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/api/campaigns/${selected.id}/content`, {
        method: "POST",
        body: JSON.stringify({ content_item_id: contentId }),
      });
      setMessage("Content linked to campaign");
      await refresh();
      setSelectedId(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Link failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Campaigns" subtitle="Plan objectives, platforms, content mix and campaign KPIs">
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Create campaign</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
            <input
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm md:col-span-2"
              placeholder="Campaign name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <select
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
            >
              <option value="awareness">Awareness</option>
              <option value="engagement">Engagement</option>
              <option value="leads">Leads</option>
              <option value="traffic">Traffic</option>
            </select>
            <input
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
              placeholder="Platforms (comma-separated)"
              value={platforms}
              onChange={(e) => setPlatforms(e.target.value)}
            />
            <input
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm md:col-span-2"
              placeholder="KPI targets"
              value={kpiTargets}
              onChange={(e) => setKpiTargets(e.target.value)}
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60 md:col-span-2"
            >
              Create
            </button>
          </form>
        </section>

        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <section className="rounded-2xl border border-ink/5 bg-white/85 p-3">
            <div className="space-y-2">
              {campaigns.length === 0 ? (
                <p className="p-3 text-sm text-ink-mute">No campaigns yet.</p>
              ) : (
                campaigns.map((campaign) => (
                  <button
                    key={campaign.id}
                    type="button"
                    className={`w-full rounded-xl border px-3 py-3 text-left ${
                      campaign.id === selectedId ? "border-tide bg-tide-soft/50" : "border-ink/5 bg-mist/30"
                    }`}
                    onClick={() => setSelectedId(campaign.id)}
                  >
                    <p className="text-sm font-medium">{campaign.name}</p>
                    <p className="mt-1 text-xs text-ink-mute">
                      {campaign.status} · {campaign.objective || "no objective"} ·{" "}
                      {campaign.content_item_ids.length} content
                    </p>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
            {!selected ? (
              <p className="text-sm text-ink-mute">Select a campaign.</p>
            ) : (
              <div className="space-y-4">
                <div>
                  <h2 className="font-display text-2xl">{selected.name}</h2>
                  <p className="mt-1 text-sm text-ink-mute">
                    {selected.status} · {selected.platforms || "no platforms"} ·{" "}
                    {selected.kpi_targets || "no KPIs"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {STATUSES.map((status) => (
                    <button
                      key={status}
                      type="button"
                      disabled={busy}
                      className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs capitalize"
                      onClick={() => void setStatus(status)}
                    >
                      {status}
                    </button>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <select
                    className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
                    value={contentId}
                    onChange={(e) => setContentId(e.target.value)}
                  >
                    <option value="">Link content item</option>
                    {contents.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title} ({item.status})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={busy || !contentId}
                    className="rounded-lg bg-tide px-3 py-2 text-sm text-white disabled:opacity-60"
                    onClick={() => void linkContent()}
                  >
                    Link content
                  </button>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">Linked content</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {selected.content_item_ids.length === 0 ? (
                      <li className="text-ink-mute">None yet</li>
                    ) : (
                      selected.content_item_ids.map((id) => {
                        const item = contents.find((c) => c.id === id);
                        return <li key={id}>{item?.title || id}</li>;
                      })
                    )}
                  </ul>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}
