"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type MediaAsset = {
  id: string;
  name: string;
  asset_type: string;
  url_or_path: string;
  prompt?: string | null;
  tags?: string | null;
  created_at: string;
};

export default function AssetsPage() {
  const { brandId, ready, user } = useAuth();
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!brandId) return;
    const list = await api<MediaAsset[]>(`/api/assets?brand_id=${brandId}`);
    setAssets(list);
  }

  useEffect(() => {
    if (!ready || !user || !brandId) return;
    void (async () => {
      try {
        const list = await api<MediaAsset[]>(`/api/assets?brand_id=${brandId}`);
        setAssets(list);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      }
    })();
  }, [ready, user, brandId]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!brandId) return;
    setBusy(true);
    setError(null);
    try {
      await api("/api/assets", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          name,
          asset_type: "image_prompt",
          url_or_path: `prompt://${name.toLowerCase().replace(/\s+/g, "-")}`,
          prompt,
          tags,
        }),
      });
      setName("");
      setPrompt("");
      setTags("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save asset");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Assets" subtitle="Centralize prompts, creative briefs and reusable media references">
      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <section className="space-y-3">
          {assets.map((asset) => (
            <article key={asset.id} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
              <h2 className="font-display text-xl">{asset.name}</h2>
              <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">{asset.asset_type}</p>
              <p className="mt-3 text-sm">{asset.prompt || asset.url_or_path}</p>
              {asset.tags ? <p className="mt-2 text-xs text-tide">{asset.tags}</p> : null}
            </article>
          ))}
          {!assets.length ? <p className="text-ink-mute">No assets yet.</p> : null}
        </section>

        <form onSubmit={onCreate} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-2xl">Add image prompt</h2>
          <label className="mt-4 block text-sm">
            Name
            <input className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="mt-3 block text-sm">
            Prompt
            <textarea className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" rows={5} value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
          </label>
          <label className="mt-3 block text-sm">
            Tags
            <input className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="reel,product,irrigation" />
          </label>
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
          <button disabled={busy || !brandId} className="mt-5 rounded-lg bg-tide px-4 py-2 text-white disabled:opacity-60">
            {busy ? "Saving…" : "Save asset"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
