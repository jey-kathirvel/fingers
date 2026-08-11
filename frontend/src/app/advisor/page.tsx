"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type Recommendation = {
  id: string;
  category: string;
  title: string;
  detail: string;
  rationale?: string | null;
  priority: string;
  status: string;
  provider: string;
  created_at: string;
};

export default function AdvisorPage() {
  const { brandId, ready, user } = useAuth();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [useLlm, setUseLlm] = useState(true);

  async function refresh() {
    if (!brandId) return;
    const list = await api<Recommendation[]>(
      `/api/advisor/recommendations?brand_id=${brandId}&status=active`,
    );
    setItems(list);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load recommendations");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId]);

  async function generate() {
    if (!brandId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const list = await api<Recommendation[]>("/api/advisor/generate", {
        method: "POST",
        body: JSON.stringify({ brand_id: brandId, use_llm: useLlm }),
      });
      setItems(list);
      setMessage(`Generated ${list.length} recommendation(s) via ${list[0]?.provider || "rules"}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: "accepted" | "dismissed") {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/advisor/recommendations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setMessage(`Marked ${status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="AI Advisor"
      subtitle="Explain performance and recommend next posts, formats and timing from stored metrics"
    >
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={busy || !brandId}
            className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={() => void generate()}
          >
            Generate recommendations
          </button>
          <label className="flex items-center gap-2 text-sm text-ink-mute">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            Use LLM refinement when available
          </label>
        </div>

        <section className="space-y-3">
          {items.length === 0 ? (
            <div className="rounded-2xl border border-ink/5 bg-white/85 p-5 text-sm text-ink-mute">
              No active recommendations yet. Sync Analytics, then generate advice grounded in your metrics,
              inbox, leads and campaigns.
            </div>
          ) : (
            items.map((item) => (
              <article key={item.id} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">
                      {item.category} · {item.priority} · {item.provider}
                    </p>
                    <h2 className="mt-1 font-display text-2xl">{item.title}</h2>
                    <p className="mt-2 text-sm text-ink">{item.detail}</p>
                    {item.rationale ? (
                      <p className="mt-2 text-xs text-ink-mute">Why: {item.rationale}</p>
                    ) : null}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-lg bg-tide px-3 py-1.5 text-xs text-white disabled:opacity-60"
                      onClick={() => void setStatus(item.id, "accepted")}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs"
                      onClick={() => void setStatus(item.id, "dismissed")}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </AppShell>
  );
}
