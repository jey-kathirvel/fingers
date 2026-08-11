"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type Term = {
  id: string;
  term: string;
  term_type: string;
  enabled: boolean;
};

type Mention = {
  id: string;
  term_id?: string | null;
  platform: string;
  author_name?: string | null;
  author_handle?: string | null;
  body: string;
  sentiment: string;
  share_weight: number;
  mentioned_at: string;
};

type Summary = {
  window_days: number;
  mention_count: number;
  by_sentiment: Record<string, number>;
  by_term_type: Record<string, number>;
  by_platform: Record<string, number>;
  share_of_voice: { term_id: string; label: string; weight: number; share_pct: number }[];
};

export default function ListeningPage() {
  const { brandId, ready, user } = useAuth();
  const [terms, setTerms] = useState<Term[]>([]);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [term, setTerm] = useState("");
  const [termType, setTermType] = useState("competitor");

  async function refresh() {
    if (!brandId) return;
    const [termList, mentionList, sum] = await Promise.all([
      api<Term[]>(`/api/listening/terms?brand_id=${brandId}`),
      api<Mention[]>(`/api/listening/mentions?brand_id=${brandId}`),
      api<Summary>(`/api/listening/summary?brand_id=${brandId}&days=14`),
    ]);
    setTerms(termList);
    setMentions(mentionList);
    setSummary(sum);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load listening");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId]);

  async function seedDefaults() {
    if (!brandId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const seeded = await api<Term[]>(`/api/listening/terms/seed-defaults?brand_id=${brandId}`, {
        method: "POST",
      });
      setMessage(`Loaded ${seeded.length} listening term(s)`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function syncMentions() {
    if (!brandId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api<{ created: number }>(`/api/listening/sync?brand_id=${brandId}`, {
        method: "POST",
      });
      setMessage(`Synced ${res.created} mention(s)`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!brandId || !term.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api("/api/listening/terms", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          term: term.trim(),
          term_type: termType,
          enabled: true,
        }),
      });
      setTerm("");
      setMessage("Term added");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleTerm(item: Term) {
    setBusy(true);
    try {
      await api(`/api/listening/terms/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !item.enabled }),
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="Listening"
      subtitle="Brand, product and competitor mention tracking with sentiment and share-of-voice"
    >
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy || !brandId}
            className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={() => void seedDefaults()}
          >
            Seed default terms
          </button>
          <button
            type="button"
            disabled={busy || !brandId}
            className="rounded-lg border border-ink/10 bg-white px-4 py-2 text-sm text-ink disabled:opacity-60"
            onClick={() => void syncMentions()}
          >
            Sync mentions
          </button>
        </div>

        {summary ? (
          <section className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-ink/5 bg-white/85 p-4">
              <p className="text-xs uppercase tracking-wide text-ink-mute">Mentions ({summary.window_days}d)</p>
              <p className="mt-1 text-2xl text-ink">{summary.mention_count}</p>
            </div>
            <div className="rounded-2xl border border-ink/5 bg-white/85 p-4">
              <p className="text-xs uppercase tracking-wide text-ink-mute">Sentiment</p>
              <p className="mt-1 text-sm text-ink">
                +{summary.by_sentiment.positive || 0} / ~{summary.by_sentiment.neutral || 0} / −
                {summary.by_sentiment.negative || 0}
              </p>
            </div>
            <div className="rounded-2xl border border-ink/5 bg-white/85 p-4">
              <p className="text-xs uppercase tracking-wide text-ink-mute">Top share of voice</p>
              <p className="mt-1 text-sm text-ink">
                {summary.share_of_voice[0]
                  ? `${summary.share_of_voice[0].label} · ${summary.share_of_voice[0].share_pct}%`
                  : "—"}
              </p>
            </div>
          </section>
        ) : null}

        {summary && summary.share_of_voice.length > 0 ? (
          <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
            <h2 className="text-sm font-semibold text-ink">Share of voice</h2>
            <ul className="mt-3 space-y-2">
              {summary.share_of_voice.map((row) => (
                <li key={row.term_id} className="flex items-center justify-between text-sm">
                  <span className="text-ink">{row.label}</span>
                  <span className="text-ink-mute">{row.share_pct}%</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <form onSubmit={onCreate} className="flex flex-wrap items-end gap-3 rounded-2xl border border-ink/5 bg-white/85 p-5">
          <label className="grow text-sm text-ink-mute">
            Term
            <input
              className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2 text-sm text-ink"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Competitor or hashtag"
            />
          </label>
          <label className="text-sm text-ink-mute">
            Type
            <select
              className="mt-1 block rounded-lg border border-ink/10 px-3 py-2 text-sm text-ink"
              value={termType}
              onChange={(e) => setTermType(e.target.value)}
            >
              <option value="brand">brand</option>
              <option value="product">product</option>
              <option value="competitor">competitor</option>
              <option value="hashtag">hashtag</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={busy || !term.trim() || !brandId}
            className="rounded-lg bg-ink px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            Add term
          </button>
        </form>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-ink">Listening terms</h2>
          {terms.length === 0 ? (
            <p className="text-sm text-ink-mute">No terms yet. Seed defaults to start from brand + competitors.</p>
          ) : (
            terms.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-xl border border-ink/5 bg-white/70 px-4 py-3 text-sm"
              >
                <span>
                  <span className="text-ink">{item.term}</span>
                  <span className="ml-2 text-xs text-ink-mute">{item.term_type}</span>
                </span>
                <button
                  type="button"
                  disabled={busy}
                  className="text-xs text-ink-mute underline"
                  onClick={() => void toggleTerm(item)}
                >
                  {item.enabled ? "Disable" : "Enable"}
                </button>
              </div>
            ))
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-ink">Recent mentions</h2>
          {mentions.length === 0 ? (
            <p className="text-sm text-ink-mute">No mentions yet. Sync after seeding terms.</p>
          ) : (
            mentions.slice(0, 25).map((m) => (
              <article key={m.id} className="rounded-2xl border border-ink/5 bg-white/85 p-4">
                <p className="text-xs text-ink-mute">
                  {m.platform} · {m.sentiment} · {m.author_handle || m.author_name} ·{" "}
                  {new Date(m.mentioned_at).toLocaleString()}
                </p>
                <p className="mt-1 text-sm text-ink">{m.body}</p>
              </article>
            ))
          )}
        </section>
      </div>
    </AppShell>
  );
}
