"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type SocialAccount = {
  id: string;
  platform: string;
  account_name: string;
  external_account_id: string | null;
  status: string;
  connection_mode: string;
  created_at: string;
};

type IntegrationHealth = {
  organization_id: string;
  connected_accounts: number;
  platforms: { platform: string; status: string }[];
  meta_configured?: boolean;
  linkedin_configured?: boolean;
  ai_provider?: string;
};

export default function IntegrationsPage() {
  const { brandId, ready, user } = useAuth();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [health, setHealth] = useState<IntegrationHealth | null>(null);
  const [platform, setPlatform] = useState("instagram");
  const [accountName, setAccountName] = useState("");
  const [connectionMode, setConnectionMode] = useState("simulation");
  const [accessToken, setAccessToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!brandId) return;
    const [accountList, healthData] = await Promise.all([
      api<SocialAccount[]>(`/api/social-accounts?brand_id=${brandId}`),
      api<IntegrationHealth>("/api/integration-health"),
    ]);
    setAccounts(accountList);
    setHealth(healthData);
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

  async function onConnect(e: FormEvent) {
    e.preventDefault();
    if (!brandId || !accountName.trim()) {
      setError("Account name is required");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api("/api/social-accounts", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          platform,
          account_name: accountName.trim(),
          connection_mode: connectionMode,
          access_token: accessToken.trim() || null,
        }),
      });
      setAccountName("");
      setAccessToken("");
      setMessage(
        connectionMode === "simulation"
          ? "Simulation account connected"
          : "Live account saved (token stored)",
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect(accountId: string) {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/social-accounts/${accountId}`, { method: "DELETE" });
      setMessage("Account disconnected");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="Integrations"
      subtitle="Connect Instagram, Facebook, and LinkedIn — simulation mode works without live OAuth"
    >
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-coral/10 px-3 py-2 text-sm text-coral">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        {health ? (
          <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
            <h2 className="font-display text-xl">Connection health</h2>
            <p className="mt-1 text-sm text-ink-mute">
              {health.connected_accounts} connected · AI {health.ai_provider || "local"} · Meta{" "}
              {health.meta_configured ? "configured" : "not set"} · LinkedIn{" "}
              {health.linkedin_configured ? "configured" : "not set"}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {health.platforms.map((item) => (
                <div key={item.platform} className="rounded-xl border border-ink/5 bg-mist/40 p-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-ink-mute">{item.platform}</p>
                  <p className="mt-1 text-sm font-medium">{item.status}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Connect account</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={onConnect}>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
              <option value="linkedin">LinkedIn</option>
            </select>
            <select
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm"
              value={connectionMode}
              onChange={(e) => setConnectionMode(e.target.value)}
            >
              <option value="simulation">Simulation</option>
              <option value="live">Live token</option>
            </select>
            <input
              className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm md:col-span-2"
              placeholder="Account display name"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
            />
            {connectionMode === "live" ? (
              <input
                className="rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm md:col-span-2"
                placeholder="Access token"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
              />
            ) : null}
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60 md:col-span-2"
            >
              Connect
            </button>
          </form>
        </section>

        <section className="rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="font-display text-xl">Connected accounts</h2>
          <div className="mt-4 space-y-3">
            {accounts.length === 0 ? (
              <p className="text-sm text-ink-mute">No social accounts yet.</p>
            ) : (
              accounts.map((account) => (
                <div
                  key={account.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink/5 bg-mist/40 p-4"
                >
                  <div>
                    <p className="text-sm font-medium">
                      {account.platform} · {account.account_name}
                    </p>
                    <p className="mt-1 text-xs text-ink-mute">
                      {account.status} · {account.connection_mode}
                      {account.external_account_id ? ` · ${account.external_account_id}` : ""}
                    </p>
                  </div>
                  {account.status === "connected" ? (
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs"
                      onClick={() => void disconnect(account.id)}
                    >
                      Disconnect
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
