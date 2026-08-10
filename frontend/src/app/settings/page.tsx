"use client";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";

export default function SettingsPage() {
  const { user, memberships, orgId } = useAuth();
  const membership = memberships.find((m) => m.organization_id === orgId);

  return (
    <AppShell title="Settings" subtitle="Account, roles and workspace controls">
      <div className="max-w-xl space-y-4 rounded-2xl border border-ink/5 bg-white/80 p-6">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-ink-mute">Signed in</p>
          <p className="mt-1 font-display text-2xl">{user?.full_name}</p>
          <p className="text-sm text-ink-mute">{user?.email}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-ink-mute">Active role</p>
          <p className="mt-1 capitalize">{membership?.role || "—"}</p>
        </div>
      </div>
    </AppShell>
  );
}
