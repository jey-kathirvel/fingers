"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type ReplyDraft = {
  id: string;
  body: string;
  tone?: string | null;
  provider: string;
  status: string;
  sent_at?: string | null;
  created_at: string;
};

type Interaction = {
  id: string;
  platform: string;
  interaction_type: string;
  author_name?: string | null;
  author_handle?: string | null;
  body: string;
  sentiment: string;
  intent: string;
  priority: string;
  lead_probability: number;
  status: string;
  received_at: string;
  responded_at?: string | null;
  drafts: ReplyDraft[];
};

type InboxStats = {
  total: number;
  new_count: number;
  draft_reply_count: number;
  responded_count: number;
  high_priority: number;
  backlog: number;
};

export default function EngagementPage() {
  const { brandId, ready, user } = useAuth();
  const [items, setItems] = useState<Interaction[]>([]);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("open");
  const [replyBody, setReplyBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) || null,
    [items, selectedId],
  );

  async function refresh() {
    if (!brandId) return;
    const statusParam =
      statusFilter === "open"
        ? ""
        : statusFilter === "all"
          ? ""
          : `&status=${statusFilter}`;
    const typeParam = typeFilter === "all" ? "" : `&interaction_type=${typeFilter}`;
    const [list, statsData] = await Promise.all([
      api<Interaction[]>(`/api/inbox?brand_id=${brandId}${statusParam}${typeParam}`),
      api<InboxStats>(`/api/inbox/stats?brand_id=${brandId}`),
    ]);
    const filtered =
      statusFilter === "open"
        ? list.filter((item) => ["new", "assigned", "draft_reply"].includes(item.status))
        : list;
    setItems(filtered);
    setStats(statsData);
    if (!selectedId && filtered[0]) setSelectedId(filtered[0].id);
    if (selectedId && !filtered.some((item) => item.id === selectedId)) {
      setSelectedId(filtered[0]?.id || "");
    }
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load inbox");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId, typeFilter, statusFilter]);

  useEffect(() => {
    if (!selected) {
      setReplyBody("");
      return;
    }
    const latest = [...(selected.drafts || [])].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
    setReplyBody(latest?.body || "");
  }, [selected]);

  async function syncInbox() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api<{ created: number }>("/api/inbox/sync", { method: "POST" });
      setMessage(`Synced ${res.created} new interaction(s)`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function draftReply() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const draft = await api<ReplyDraft>(`/api/interactions/${selected.id}/reply-draft`, {
        method: "POST",
        body: JSON.stringify({ tone: "helpful" }),
      });
      setReplyBody(draft.body);
      setMessage(`AI draft ready (${draft.provider})`);
      await refresh();
      setSelectedId(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft failed");
    } finally {
      setBusy(false);
    }
  }

  async function approveSend() {
    if (!selected || !replyBody.trim()) {
      setError("Reply body is required");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const latest = [...(selected.drafts || [])].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
      await api(`/api/interactions/${selected.id}/approve-send`, {
        method: "POST",
        body: JSON.stringify({
          draft_id: latest?.id || null,
          body: replyBody.trim(),
        }),
      });
      setMessage("Reply approved & sent (simulation)");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(status: string) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/api/interactions/${selected.id}`, {
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

  async function convertLead() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const lead = await api<{ id: string; score: number }>(`/api/interactions/${selected.id}/convert-lead`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setMessage(`Lead created (score ${lead.score}) — open Leads to continue follow-up`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Convert failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Engagement" subtitle="Unified inbox for comments, messages, mentions and reviews">
      <div className="space-y-4">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={() => void syncInbox()}
          >
            Sync inbox
          </button>
          <select
            className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="open">Open</option>
            <option value="all">All</option>
            <option value="new">New</option>
            <option value="draft_reply">Draft reply</option>
            <option value="responded">Responded</option>
            <option value="ignored">Ignored</option>
          </select>
          <select
            className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="all">All types</option>
            <option value="comment">Comments</option>
            <option value="message">Messages</option>
            <option value="mention">Mentions</option>
            <option value="review">Reviews</option>
          </select>
          {stats ? (
            <p className="text-sm text-ink-mute">
              {stats.backlog} backlog · {stats.high_priority} high priority · {stats.total} total
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.1fr_1.4fr]">
          <section className="rounded-2xl border border-ink/5 bg-white/85 p-3">
            <div className="space-y-2">
              {items.length === 0 ? (
                <p className="p-3 text-sm text-ink-mute">
                  No interactions yet. Connect a social account, then Sync inbox.
                </p>
              ) : (
                items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`w-full rounded-xl border px-3 py-3 text-left ${
                      item.id === selectedId ? "border-tide bg-tide-soft/50" : "border-ink/5 bg-mist/30"
                    }`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">
                        {item.author_name || item.author_handle || "Unknown"} · {item.interaction_type}
                      </p>
                      <span className="text-xs uppercase tracking-wide text-ink-mute">{item.priority}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-ink-mute">{item.body}</p>
                    <p className="mt-2 text-xs text-ink-mute">
                      {item.platform} · {item.intent} · {item.sentiment} · {item.status}
                    </p>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
            {!selected ? (
              <p className="text-sm text-ink-mute">Select an interaction to reply.</p>
            ) : (
              <div className="space-y-4">
                <div>
                  <h2 className="font-display text-2xl">
                    {selected.author_name || selected.author_handle || "Unknown"}
                  </h2>
                  <p className="mt-1 text-sm text-ink-mute">
                    {selected.platform} · {selected.interaction_type} · {selected.status} · lead{" "}
                    {selected.lead_probability}%
                  </p>
                  <p className="mt-4 whitespace-pre-wrap text-sm">{selected.body}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg bg-tide px-3 py-2 text-sm text-white disabled:opacity-60"
                    onClick={() => void draftReply()}
                  >
                    Suggest AI reply
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
                    onClick={() => void setStatus("ignored")}
                  >
                    Ignore
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
                    onClick={() => void setStatus("closed")}
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg border border-ink/10 px-3 py-2 text-sm"
                    onClick={() => void convertLead()}
                  >
                    Convert to lead
                  </button>
                </div>

                <div>
                  <label className="text-xs uppercase tracking-[0.14em] text-ink-mute">Reply</label>
                  <textarea
                    className="mt-2 min-h-32 w-full rounded-xl border border-ink/10 bg-white px-3 py-2 text-sm"
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    placeholder="AI suggestion appears here — edit, then Approve & Send"
                  />
                  <button
                    type="button"
                    disabled={busy || !replyBody.trim()}
                    className="mt-3 rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
                    onClick={() => void approveSend()}
                  >
                    Approve & Send
                  </button>
                </div>

                {selected.drafts?.length ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">Draft history</p>
                    <div className="mt-2 space-y-2">
                      {selected.drafts.map((draft) => (
                        <div key={draft.id} className="rounded-lg border border-ink/5 bg-mist/40 px-3 py-2 text-sm">
                          <p className="text-xs text-ink-mute">
                            {draft.status} · {draft.provider}
                            {draft.sent_at ? ` · sent ${new Date(draft.sent_at).toLocaleString()}` : ""}
                          </p>
                          <p className="mt-1">{draft.body}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}
