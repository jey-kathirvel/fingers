"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type ContentVersion = {
  id: string;
  platform: string;
  body?: string | null;
  headline?: string | null;
};

type ContentItem = {
  id: string;
  title: string;
  status: string;
  brand_id: string;
  versions: ContentVersion[];
};

type SocialAccount = {
  id: string;
  platform: string;
  account_name: string;
  status: string;
  connection_mode: string;
};

type ScheduledPost = {
  id: string;
  content_item_id: string;
  content_version_id: string;
  social_account_id: string;
  platform: string;
  scheduled_for: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  published_at: string | null;
  external_post_id: string | null;
};

type CalendarItem = {
  id: string;
  title: string;
  platform: string;
  status: string;
  scheduled_for: string;
  content_item_id: string;
  brand_id: string;
  account_name?: string | null;
};

type PublishingLog = {
  id: string;
  scheduled_post_id: string | null;
  platform: string;
  action: string;
  status: string;
  message: string | null;
  created_at: string;
};

export default function PublishingPage() {
  const { brandId, ready, user } = useAuth();
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [calendar, setCalendar] = useState<CalendarItem[]>([]);
  const [logs, setLogs] = useState<PublishingLog[]>([]);
  const [contentId, setContentId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selectedContent = useMemo(
    () => contents.find((item) => item.id === contentId) || null,
    [contents, contentId],
  );

  const matchingAccounts = useMemo(() => {
    const platform = selectedContent?.versions.find((v) => v.id === versionId)?.platform;
    if (!platform) return accounts.filter((a) => a.status === "connected");
    return accounts.filter((a) => a.status === "connected" && a.platform === platform);
  }, [accounts, selectedContent, versionId]);

  async function refresh() {
    if (!brandId) return;
    const [contentList, accountList, postList, calendarItems, logList] = await Promise.all([
      api<ContentItem[]>(`/api/content?brand_id=${brandId}`),
      api<SocialAccount[]>(`/api/social-accounts?brand_id=${brandId}`),
      api<ScheduledPost[]>(`/api/scheduled-posts?brand_id=${brandId}`),
      api<CalendarItem[]>(`/api/calendar?brand_id=${brandId}&days=45`),
      api<PublishingLog[]>("/api/publishing-logs"),
    ]);
    setContents(contentList);
    setAccounts(accountList);
    setPosts(postList);
    setCalendar(calendarItems);
    setLogs(logList);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh when brand/session changes
  }, [ready, user, brandId]);

  useEffect(() => {
    if (!selectedContent) {
      setVersionId("");
      return;
    }
    if (!selectedContent.versions.some((v) => v.id === versionId)) {
      setVersionId(selectedContent.versions[0]?.id || "");
    }
  }, [selectedContent, versionId]);

  const schedulable = contents.filter((item) =>
    ["approved", "scheduled", "draft", "review"].includes(item.status),
  );
  const filteredPosts =
    statusFilter === "all" ? posts : posts.filter((post) => post.status === statusFilter);

  async function onSchedule(e: FormEvent) {
    e.preventDefault();
    if (!contentId || !versionId || !accountId || !scheduledFor) {
      setError("Select content, platform version, account, and time");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api("/api/scheduled-posts", {
        method: "POST",
        body: JSON.stringify({
          content_item_id: contentId,
          content_version_id: versionId,
          social_account_id: accountId,
          scheduled_for: new Date(scheduledFor).toISOString(),
        }),
      });
      setMessage("Post scheduled");
      setScheduledFor("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Schedule failed");
    } finally {
      setBusy(false);
    }
  }

  async function publishNow() {
    if (!contentId || !versionId || !accountId) {
      setError("Select content, platform version, and account");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api("/api/publishing/publish-now", {
        method: "POST",
        body: JSON.stringify({
          content_item_id: contentId,
          content_version_id: versionId,
          social_account_id: accountId,
        }),
      });
      setMessage("Published now (simulation or live adapter)");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setBusy(false);
    }
  }

  async function retryPost(postId: string) {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/scheduled-posts/${postId}/retry`, { method: "POST" });
      setMessage("Retry queued");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setBusy(false);
    }
  }

  async function cancelPost(postId: string) {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/scheduled-posts/${postId}`, { method: "DELETE" });
      setMessage("Schedule cancelled");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Publishing" subtitle="Schedule approved variants, publish now, and review worker logs">
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Schedule / publish</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onSchedule}>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={contentId}
              onChange={(e) => setContentId(e.target.value)}
            >
              <option value="">Content item</option>
              {schedulable.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title} ({item.status})
                </option>
              ))}
            </select>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
            >
              <option value="">Platform version</option>
              {(selectedContent?.versions || []).map((version) => (
                <option key={version.id} value={version.id}>
                  {version.platform}
                </option>
              ))}
            </select>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
            >
              <option value="">Social account</option>
              {matchingAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.platform} · {account.account_name} ({account.connection_mode})
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={scheduledFor}
              onChange={(e) => setScheduledFor(e.target.value)}
            />
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
              >
                Schedule
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-lg border border-ink/10 px-4 py-2 text-sm disabled:opacity-60"
                onClick={() => void publishNow()}
              >
                Publish now
              </button>
            </div>
          </form>
          {!accounts.some((a) => a.status === "connected") ? (
            <p className="mt-3 text-sm text-ink-mute">
              Connect a simulation account under Integrations before publishing.
            </p>
          ) : null}
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Calendar</h2>
          <div className="mt-4 space-y-2">
            {calendar.length === 0 ? (
              <p className="text-sm text-ink-mute">No posts in the calendar window.</p>
            ) : (
              calendar.map((item) => (
                <div key={item.id} className="rounded-xl border border-ink/5 bg-mist/40 px-4 py-3">
                  <p className="text-sm font-medium">
                    {item.title} · {item.platform} · {item.status}
                  </p>
                  <p className="text-xs text-ink-mute">
                    {new Date(item.scheduled_for).toLocaleString()}
                    {item.account_name ? ` · ${item.account_name}` : ""}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-xl">Scheduled posts</h2>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All</option>
              <option value="scheduled">Scheduled</option>
              <option value="publishing">Publishing</option>
              <option value="published">Published</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div className="mt-4 space-y-3">
            {filteredPosts.length === 0 ? (
              <p className="text-sm text-ink-mute">No posts in this filter.</p>
            ) : (
              filteredPosts.map((post) => (
                <article key={post.id} className="rounded-xl border border-ink/5 bg-mist/40 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">
                        {post.platform} · {post.status}
                      </p>
                      <p className="mt-1 text-xs text-ink-mute">
                        {new Date(post.scheduled_for).toLocaleString()} · attempts {post.attempt_count}/
                        {post.max_attempts}
                      </p>
                      {post.external_post_id ? (
                        <p className="mt-1 text-xs text-ink-mute">External: {post.external_post_id}</p>
                      ) : null}
                      {post.last_error ? <p className="mt-1 text-xs text-red-700">{post.last_error}</p> : null}
                    </div>
                    <div className="flex gap-2">
                      {post.status === "failed" || post.status === "scheduled" ? (
                        <button
                          type="button"
                          disabled={busy}
                          className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs"
                          onClick={() => void retryPost(post.id)}
                        >
                          {post.status === "failed" ? "Retry" : "Publish now"}
                        </button>
                      ) : null}
                      {post.status === "scheduled" ? (
                        <button
                          type="button"
                          disabled={busy}
                          className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs"
                          onClick={() => void cancelPost(post.id)}
                        >
                          Cancel
                        </button>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Publishing logs</h2>
          <div className="mt-4 space-y-2">
            {logs.length === 0 ? (
              <p className="text-sm text-ink-mute">No logs yet.</p>
            ) : (
              logs.slice(0, 40).map((log) => (
                <div key={log.id} className="rounded-lg border border-ink/5 px-3 py-2 text-sm">
                  <span className="font-medium">{log.platform}</span>
                  <span className="mx-2 text-ink-mute">·</span>
                  <span>{log.action}</span>
                  <span className="mx-2 text-ink-mute">·</span>
                  <span>{log.status}</span>
                  {log.message ? <span className="mx-2 text-ink-mute">· {log.message}</span> : null}
                  <span className="float-right text-xs text-ink-mute">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
