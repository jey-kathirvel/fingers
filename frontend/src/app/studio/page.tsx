"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type ContentVersion = {
  id: string;
  platform: string;
  format?: string | null;
  headline?: string | null;
  body?: string | null;
  hashtags?: string | null;
  cta?: string | null;
  image_prompt?: string | null;
  video_script?: string | null;
  score_clarity?: number | null;
  score_brand_fit?: number | null;
  score_cta?: number | null;
  score_platform_fit?: number | null;
};

type ContentItem = {
  id: string;
  title: string;
  topic?: string | null;
  objective?: string | null;
  master_concept?: string | null;
  status: string;
  versions: ContentVersion[];
  updated_at: string;
};

type ContentIdea = {
  id: string;
  title: string;
  format?: string | null;
  goal?: string | null;
  platforms?: string | null;
  confidence?: string | null;
  rationale?: string | null;
};

const PLATFORMS = [
  { id: "linkedin", label: "LinkedIn" },
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "x", label: "X" },
  { id: "youtube", label: "YouTube" },
];

export default function StudioPage() {
  const { brandId, brands, ready, user } = useAuth();
  const [tab, setTab] = useState<"create" | "ideas" | "drafts">("create");
  const [topic, setTopic] = useState("Promote our irrigation-management feature this week");
  const [objective, setObjective] = useState("awareness");
  const [platforms, setPlatforms] = useState<string[]>(["linkedin", "instagram", "facebook"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState<ContentItem | null>(null);
  const [drafts, setDrafts] = useState<ContentItem[]>([]);
  const [ideas, setIdeas] = useState<ContentIdea[]>([]);
  const [rewriteText, setRewriteText] = useState("");
  const [rewriteResult, setRewriteResult] = useState<string | null>(null);

  const activeBrand = useMemo(() => brands.find((b) => b.id === brandId), [brands, brandId]);

  async function refreshDrafts() {
    if (!brandId) return;
    const list = await api<ContentItem[]>(`/api/content?brand_id=${brandId}`);
    setDrafts(list);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        const list = await api<ContentItem[]>(`/api/content?brand_id=${brandId}`);
        setDrafts(list);
        const ideaList = await api<ContentIdea[]>(`/api/ai/ideas?brand_id=${brandId}`);
        setIdeas(ideaList);
      } catch {
        /* ignore initial load errors */
      }
    })();
  }, [ready, user, brandId]);

  function togglePlatform(id: string) {
    setPlatforms((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
  }

  async function onGenerate(e: FormEvent) {
    e.preventDefault();
    if (!brandId || platforms.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const item = await api<ContentItem>("/api/ai/generate", {
        method: "POST",
        body: JSON.stringify({ brand_id: brandId, topic, objective, platforms, save: true }),
      });
      setGenerated(item);
      setRewriteText(item.versions[0]?.body || "");
      await refreshDrafts();
      setTab("drafts");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function onIdeas() {
    if (!brandId) return;
    setBusy(true);
    setError(null);
    try {
      const list = await api<ContentIdea[]>("/api/ai/ideas", {
        method: "POST",
        body: JSON.stringify({ brand_id: brandId, count: 5, persist: true }),
      });
      setIdeas(list);
      setTab("ideas");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ideas failed");
    } finally {
      setBusy(false);
    }
  }

  async function applyIdea(idea: ContentIdea) {
    setTopic(idea.title);
    if (idea.platforms) {
      setPlatforms(
        idea.platforms
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
      );
    }
    if (idea.goal) setObjective(idea.goal);
    setTab("create");
  }

  async function setStatus(id: string, status: string) {
    setBusy(true);
    try {
      await api(`/api/content/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await refreshDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRewrite(e: FormEvent) {
    e.preventDefault();
    if (!brandId || !rewriteText) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api<{ body: string }>("/api/ai/rewrite", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          platform: platforms[0] || "linkedin",
          text: rewriteText,
          instruction: "Make the hook stronger and CTA clearer",
        }),
      });
      setRewriteResult(res.body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rewrite failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="AI Studio"
      subtitle={activeBrand ? `Brand: ${activeBrand.name}` : "Generate platform-specific social content"}
    >
      <div className="mb-6 flex flex-wrap gap-2">
        {(
          [
            ["create", "Create content"],
            ["ideas", "Ideas"],
            ["drafts", "Drafts"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`rounded-lg px-4 py-2 text-sm ${tab === id ? "bg-tide text-white" : "bg-white text-ink-soft"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="mb-4 text-sm text-red-700">{error}</p> : null}

      {tab === "create" ? (
        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <form onSubmit={onGenerate} className="rounded-2xl border border-ink/5 bg-white/85 p-5 shadow-sm">
            <h2 className="font-display text-2xl">Describe the goal</h2>
            <p className="mt-1 text-sm text-ink-mute">Fingers engineers channel-native variants, not one generic post.</p>
            <label className="mt-4 block text-sm">
              Topic / business goal
              <textarea
                className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2"
                rows={4}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </label>
            <label className="mt-3 block text-sm">
              Objective
              <select
                className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              >
                <option value="awareness">Awareness</option>
                <option value="education">Education</option>
                <option value="engagement">Engagement</option>
                <option value="leads">Leads</option>
                <option value="product">Product</option>
              </select>
            </label>
            <div className="mt-4">
              <p className="text-sm">Platforms</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    className={`rounded-lg px-3 py-1.5 text-sm ${
                      platforms.includes(p.id) ? "bg-ink text-white" : "bg-mist text-ink-soft"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button disabled={busy || !brandId} className="rounded-lg bg-tide px-4 py-2 text-white disabled:opacity-60">
                {busy ? "Engineering…" : "Generate variants"}
              </button>
              <button type="button" disabled={busy || !brandId} onClick={() => void onIdeas()} className="rounded-lg bg-ink px-4 py-2 text-white disabled:opacity-60">
                Suggest ideas
              </button>
            </div>
          </form>

          <div className="space-y-4">
            <form onSubmit={onRewrite} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
              <h2 className="font-display text-2xl">Rewrite</h2>
              <textarea
                className="mt-3 w-full rounded-lg border border-ink/10 px-3 py-2 text-sm"
                rows={6}
                value={rewriteText}
                onChange={(e) => setRewriteText(e.target.value)}
                placeholder="Paste a draft to rewrite"
              />
              <button disabled={busy} className="mt-3 rounded-lg bg-ink px-4 py-2 text-sm text-white disabled:opacity-60">
                Strengthen hook + CTA
              </button>
              {rewriteResult ? (
                <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-mist p-3 text-sm">{rewriteResult}</pre>
              ) : null}
            </form>
            {generated ? (
              <div className="rounded-2xl border border-ink/5 bg-white/85 p-5">
                <h2 className="font-display text-2xl">{generated.title}</h2>
                <p className="mt-2 text-sm text-ink-mute">{generated.master_concept}</p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {tab === "ideas" ? (
        <div className="grid gap-3 md:grid-cols-2">
          {ideas.map((idea) => (
            <article key={idea.id} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-tide">{idea.confidence} confidence</p>
              <h3 className="mt-2 font-display text-xl">{idea.title}</h3>
              <p className="mt-2 text-sm text-ink-mute">
                {idea.format} · {idea.goal} · {idea.platforms}
              </p>
              <p className="mt-2 text-sm">{idea.rationale}</p>
              <button className="mt-4 rounded-lg bg-tide px-3 py-1.5 text-sm text-white" onClick={() => void applyIdea(idea)}>
                Generate post
              </button>
            </article>
          ))}
          {!ideas.length ? <p className="text-ink-mute">No ideas yet. Use “Suggest ideas”.</p> : null}
        </div>
      ) : null}

      {tab === "drafts" ? (
        <div className="space-y-4">
          {drafts.map((item) => (
            <article key={item.id} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-2xl">{item.title}</h3>
                  <p className="text-sm text-ink-mute">
                    {item.status} · {item.versions.length} platform version(s)
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {item.status === "draft" ? (
                    <button className="rounded-lg bg-ink px-3 py-1.5 text-xs text-white" onClick={() => void setStatus(item.id, "review")}>
                      Send to review
                    </button>
                  ) : null}
                  {item.status === "review" ? (
                    <button className="rounded-lg bg-tide px-3 py-1.5 text-xs text-white" onClick={() => void setStatus(item.id, "approved")}>
                      Approve
                    </button>
                  ) : null}
                </div>
              </div>
              <p className="mt-3 text-sm text-ink-soft">{item.master_concept}</p>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {item.versions.map((v) => (
                  <div key={v.id} className="rounded-xl bg-mist p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium capitalize">{v.platform}</p>
                      <p className="text-xs text-ink-mute">
                        fit {v.score_platform_fit ?? "—"} · cta {v.score_cta ?? "—"}
                      </p>
                    </div>
                    {v.headline ? <p className="mt-2 font-medium">{v.headline}</p> : null}
                    <pre className="mt-2 whitespace-pre-wrap font-sans text-ink-soft">{v.body}</pre>
                    {v.hashtags ? <p className="mt-2 text-xs text-tide">{v.hashtags}</p> : null}
                    {v.image_prompt ? <p className="mt-2 text-xs text-ink-mute">Image: {v.image_prompt}</p> : null}
                    {v.video_script ? <pre className="mt-2 whitespace-pre-wrap font-sans text-xs text-ink-mute">{v.video_script}</pre> : null}
                  </div>
                ))}
              </div>
            </article>
          ))}
          {!drafts.length ? <p className="text-ink-mute">No drafts yet. Generate your first multi-platform concept.</p> : null}
        </div>
      ) : null}
    </AppShell>
  );
}
