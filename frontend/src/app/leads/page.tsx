"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type Lead = {
  id: string;
  name: string;
  source_platform?: string | null;
  intent?: string | null;
  score: number;
  status: string;
  product_interest?: string | null;
  follow_up_at?: string | null;
  source_message?: string | null;
  notes?: string | null;
  campaign_id?: string | null;
  created_at: string;
};

type Pipeline = {
  total: number;
  by_status: Record<string, number>;
  converted: number;
  open_count: number;
  avg_score: number;
};

type Campaign = { id: string; name: string };

const STATUSES = ["new", "contacted", "interested", "demo", "proposal", "converted", "lost"];

export default function LeadsPage() {
  const { brandId, ready, user } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [productInterest, setProductInterest] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = leads.find((l) => l.id === selectedId) || null;

  async function refresh() {
    if (!brandId) return;
    const statusParam = statusFilter === "all" || statusFilter === "open" ? "" : `&status=${statusFilter}`;
    const [leadRows, pipe, camps] = await Promise.all([
      api<Lead[]>(`/api/leads?brand_id=${brandId}${statusParam}`),
      api<Pipeline>(`/api/leads/pipeline?brand_id=${brandId}`),
      api<Campaign[]>(`/api/campaigns?brand_id=${brandId}`),
    ]);
    const filtered =
      statusFilter === "open"
        ? leadRows.filter((l) => !["converted", "lost"].includes(l.status))
        : leadRows;
    setLeads(filtered);
    setPipeline(pipe);
    setCampaigns(camps);
    if (!selectedId && filtered[0]) setSelectedId(filtered[0].id);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load leads");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId, statusFilter]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!brandId || !name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api<Lead>("/api/leads", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          name: name.trim(),
          product_interest: productInterest || null,
          score: 40,
          status: "new",
          source_platform: "manual",
        }),
      });
      setName("");
      setProductInterest("");
      setMessage("Lead created");
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
      await api(`/api/leads/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setMessage(`Lead marked ${status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function attachCampaign(campaignId: string) {
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/api/leads/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ campaign_id: campaignId || null }),
      });
      setMessage("Campaign attribution updated");
      await refresh();
      setSelectedId(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Leads" subtitle="Convert social conversations into scored follow-up pipeline">
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        {pipeline ? (
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Total leads" value={pipeline.total} />
            <Stat label="Open" value={pipeline.open_count} />
            <Stat label="Converted" value={pipeline.converted} />
            <Stat label="Avg score" value={pipeline.avg_score} />
          </section>
        ) : null}

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Add lead</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={onCreate}>
            <input
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
              placeholder="Name / profile"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
              placeholder="Product interest"
              value={productInterest}
              onChange={(e) => setProductInterest(e.target.value)}
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            >
              Create lead
            </button>
          </form>
          <p className="mt-2 text-xs text-ink-mute">
            Tip: convert from Engagement inbox for full source attribution.
          </p>
        </section>

        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="open">Open</option>
            <option value="all">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <section className="rounded-2xl border border-ink/5 bg-white/85 p-3">
            <div className="space-y-2">
              {leads.length === 0 ? (
                <p className="p-3 text-sm text-ink-mute">No leads yet.</p>
              ) : (
                leads.map((lead) => (
                  <button
                    key={lead.id}
                    type="button"
                    className={`w-full rounded-xl border px-3 py-3 text-left ${
                      lead.id === selectedId ? "border-tide bg-tide-soft/50" : "border-ink/5 bg-mist/30"
                    }`}
                    onClick={() => setSelectedId(lead.id)}
                  >
                    <p className="text-sm font-medium">
                      {lead.name} · score {lead.score}
                    </p>
                    <p className="mt-1 text-xs text-ink-mute">
                      {lead.status} · {lead.source_platform || "unknown"} · {lead.intent || "n/a"}
                    </p>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
            {!selected ? (
              <p className="text-sm text-ink-mute">Select a lead.</p>
            ) : (
              <div className="space-y-4">
                <div>
                  <h2 className="font-display text-2xl">{selected.name}</h2>
                  <p className="mt-1 text-sm text-ink-mute">
                    {selected.status} · score {selected.score} · {selected.source_platform || "manual"}
                  </p>
                  {selected.source_message ? (
                    <p className="mt-3 whitespace-pre-wrap text-sm">{selected.source_message}</p>
                  ) : null}
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
                <select
                  className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
                  value={selected.campaign_id || ""}
                  onChange={(e) => void attachCampaign(e.target.value)}
                >
                  <option value="">No campaign attribution</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-ink/5 bg-white/85 p-4">
      <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">{label}</p>
      <p className="mt-2 font-display text-3xl tracking-tight">{value}</p>
    </div>
  );
}
