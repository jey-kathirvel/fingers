"use client";

import { AppShell } from "@/components/app-shell";

export default function ComingSoon({
  title,
  phase,
  detail,
}: {
  title: string;
  phase: string;
  detail: string;
}) {
  return (
    <AppShell title={title} subtitle={`${phase} · foundation ready`}>
      <div className="max-w-2xl rounded-2xl border border-ink/5 bg-white/80 p-6 shadow-sm">
        <p className="text-xs uppercase tracking-[0.18em] text-tide">{phase}</p>
        <h2 className="mt-2 font-display text-3xl tracking-tight">Coming next</h2>
        <p className="mt-3 text-ink-mute">{detail}</p>
      </div>
    </AppShell>
  );
}
