"use client";

import { FormEvent, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiFetch, type Brand } from "@/lib/utils";

export default function SettingsPage() {
  const { token, context, brands, refresh } = useAuth();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!token || !context?.organization?.id) return;
    setMessage(null);
    setError(null);
    try {
      await apiFetch<Brand>(
        "/brands",
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: context.organization.id,
            name,
            description,
          }),
        },
        token,
      );
      setName("");
      setDescription("");
      setMessage("Brand created.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create brand");
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="glass shadow-soft rounded-[1.75rem] p-6">
        <h2 className="display text-3xl text-ink">Brands</h2>
        <p className="mt-2 text-sm text-ink/65">
          Create and switch brands within your organization. Tenant scoping is
          enforced by the API.
        </p>
        <ul className="mt-5 space-y-3">
          {brands.map((brand) => (
            <li key={brand.id} className="rounded-2xl bg-mist/60 px-4 py-3">
              <p className="font-medium text-ink">{brand.name}</p>
              <p className="text-sm text-ink/60">{brand.description || "No description"}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="glass shadow-soft rounded-[1.75rem] p-6">
        <h2 className="display text-3xl text-ink">Create brand</h2>
        <form onSubmit={onCreate} className="mt-5 space-y-4">
          <label className="block text-sm">
            <span className="mb-1.5 block text-ink/70">Name</span>
            <input
              className="w-full rounded-xl border border-[var(--line)] bg-white/80 px-3 py-2.5 outline-none"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-ink/70">Description</span>
            <textarea
              className="min-h-28 w-full rounded-xl border border-[var(--line)] bg-white/80 px-3 py-2.5 outline-none"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          {message ? <p className="text-sm text-forest">{message}</p> : null}
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          <button className="rounded-xl bg-forest px-4 py-2.5 text-sm font-semibold text-white hover:bg-forest-deep">
            Save brand
          </button>
        </form>
      </div>
    </div>
  );
}
