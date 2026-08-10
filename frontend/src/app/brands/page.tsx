"use client";

import { FormEvent, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api, type Brand } from "@/lib/api";

export default function BrandsPage() {
  const { brands, refreshBrands, setBrandId } = useAuth();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const brand = await api<Brand>("/api/brands", {
        method: "POST",
        body: JSON.stringify({ name, slug, description }),
      });
      await refreshBrands();
      setBrandId(brand.id);
      setName("");
      setSlug("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create brand");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell title="Brands" subtitle="Multi-brand workspace profiles and voice settings">
      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <section className="space-y-3">
          {brands.map((brand) => (
            <article key={brand.id} className="rounded-2xl border border-ink/5 bg-white/80 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-display text-2xl">{brand.name}</h2>
                  <p className="text-sm text-ink-mute">{brand.slug}</p>
                </div>
                <button
                  className="rounded-lg bg-ink px-3 py-1.5 text-xs text-white"
                  onClick={() => setBrandId(brand.id)}
                >
                  Switch
                </button>
              </div>
              <p className="mt-3 text-sm text-ink-soft">{brand.description || "No description yet"}</p>
              {brand.tone_of_voice ? (
                <p className="mt-2 text-xs text-ink-mute">Tone: {brand.tone_of_voice}</p>
              ) : null}
            </article>
          ))}
        </section>

        <form onSubmit={onCreate} className="rounded-2xl border border-ink/5 bg-white/80 p-5">
          <h2 className="font-display text-2xl">Create brand</h2>
          <label className="mt-4 block text-sm">
            Name
            <input className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="mt-3 block text-sm">
            Slug
            <input className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" value={slug} onChange={(e) => setSlug(e.target.value)} pattern="^[a-z0-9-]+$" required />
          </label>
          <label className="mt-3 block text-sm">
            Description
            <textarea className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
          <button disabled={saving} className="mt-5 rounded-lg bg-tide px-4 py-2 text-white disabled:opacity-60">
            {saving ? "Saving…" : "Save brand"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
