"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";

type Rule = {
  id: string;
  name: string;
  description?: string | null;
  enabled: boolean;
  trigger_type: string;
  trigger_config_json?: string | null;
  action_type: string;
  action_config_json?: string | null;
  last_run_at?: string | null;
};

type Run = {
  id: string;
  rule_id: string;
  status: string;
  trigger_entity_type?: string | null;
  trigger_entity_id?: string | null;
  result_json?: string | null;
  error_message?: string | null;
  created_at: string;
};

export default function AutomationsPage() {
  const { brandId, ready, user } = useAuth();
  const [rules, setRules] = useState<Rule[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState("inbox_keyword");
  const [actionType, setActionType] = useState("create_lead");
  const [triggerConfig, setTriggerConfig] = useState('{"keywords":["price","pricing"]}');
  const [actionConfig, setActionConfig] = useState('{"also_draft_reply":true,"intent":"sales_enquiry"}');

  async function refresh() {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    const [ruleList, runList] = await Promise.all([
      api<Rule[]>(`/api/automations${qs}`),
      api<Run[]>("/api/automations/runs"),
    ]);
    setRules(ruleList);
    setRuns(runList);
  }

  useEffect(() => {
    if (!ready || !user) return;
    void (async () => {
      try {
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load automations");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, brandId]);

  async function seedDefaults() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const qs = brandId ? `?brand_id=${brandId}` : "";
      const seeded = await api<Rule[]>(`/api/automations/seed-defaults${qs}`, { method: "POST" });
      setMessage(`Loaded ${seeded.length} default rule(s)`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function runNow() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const qs = brandId ? `?brand_id=${brandId}` : "";
      const summary = await api<{ rules_evaluated: number; runs: number; success: number; failed: number }>(
        `/api/automations/run${qs}`,
        { method: "POST" },
      );
      setMessage(
        `Evaluated ${summary.rules_evaluated} rule(s) → ${summary.runs} run(s) (${summary.success} ok / ${summary.failed} failed)`,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api<Rule>("/api/automations", {
        method: "POST",
        body: JSON.stringify({
          brand_id: brandId,
          name: name.trim(),
          trigger_type: triggerType,
          action_type: actionType,
          trigger_config_json: triggerConfig,
          action_config_json: actionConfig,
          enabled: true,
        }),
      });
      setName("");
      setMessage("Rule created");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEnabled(rule: Rule) {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/automations/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
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
      title="Automations"
      subtitle="Rule-based, auditable actions for replies, leads, alerts and reporting"
    >
      <div className="space-y-6">
        {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-xl bg-mist-deep px-3 py-2 text-sm text-ink">{message}</p> : null}

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy}
            className="rounded-lg bg-tide px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={() => void seedDefaults()}
          >
            Seed default rules
          </button>
          <button
            type="button"
            disabled={busy}
            className="rounded-lg border border-ink/10 bg-white px-4 py-2 text-sm text-ink disabled:opacity-60"
            onClick={() => void runNow()}
          >
            Run rules now
          </button>
        </div>

        <form onSubmit={onCreate} className="space-y-3 rounded-2xl border border-ink/5 bg-white/85 p-5">
          <h2 className="text-sm font-semibold text-ink">New rule</h2>
          <input
            className="w-full rounded-lg border border-ink/10 px-3 py-2 text-sm"
            placeholder="Rule name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm text-ink-mute">
              Trigger
              <select
                className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2 text-sm text-ink"
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value)}
              >
                <option value="inbox_keyword">inbox_keyword</option>
                <option value="negative_sentiment">negative_sentiment</option>
                <option value="unanswered_sla">unanswered_sla</option>
                <option value="publish_failed">publish_failed</option>
                <option value="high_engagement">high_engagement</option>
              </select>
            </label>
            <label className="text-sm text-ink-mute">
              Action
              <select
                className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2 text-sm text-ink"
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
              >
                <option value="create_lead">create_lead</option>
                <option value="notify">notify</option>
                <option value="draft_reply">draft_reply</option>
                <option value="classify_intent">classify_intent</option>
                <option value="escalate">escalate</option>
              </select>
            </label>
          </div>
          <label className="block text-sm text-ink-mute">
            Trigger config (JSON)
            <textarea
              className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2 font-mono text-xs text-ink"
              rows={2}
              value={triggerConfig}
              onChange={(e) => setTriggerConfig(e.target.value)}
            />
          </label>
          <label className="block text-sm text-ink-mute">
            Action config (JSON)
            <textarea
              className="mt-1 w-full rounded-lg border border-ink/10 px-3 py-2 font-mono text-xs text-ink"
              rows={2}
              value={actionConfig}
              onChange={(e) => setActionConfig(e.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="rounded-lg bg-ink px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            Create rule
          </button>
        </form>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-ink">Rules ({rules.length})</h2>
          {rules.length === 0 ? (
            <p className="text-sm text-ink-mute">No rules yet. Seed defaults or create one above.</p>
          ) : (
            rules.map((rule) => (
              <article key={rule.id} className="rounded-2xl border border-ink/5 bg-white/85 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium text-ink">{rule.name}</h3>
                    <p className="mt-1 text-sm text-ink-mute">{rule.description || "—"}</p>
                    <p className="mt-2 text-xs text-ink-mute">
                      WHEN <span className="text-ink">{rule.trigger_type}</span> → THEN{" "}
                      <span className="text-ink">{rule.action_type}</span>
                      {rule.last_run_at ? ` · last run ${new Date(rule.last_run_at).toLocaleString()}` : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs text-ink disabled:opacity-60"
                    onClick={() => void toggleEnabled(rule)}
                  >
                    {rule.enabled ? "Disable" : "Enable"}
                  </button>
                </div>
              </article>
            ))
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-ink">Recent runs</h2>
          {runs.length === 0 ? (
            <p className="text-sm text-ink-mute">No automation runs recorded yet.</p>
          ) : (
            <ul className="space-y-2">
              {runs.slice(0, 20).map((run) => (
                <li key={run.id} className="rounded-xl border border-ink/5 bg-white/70 px-4 py-3 text-sm">
                  <span className={run.status === "success" ? "text-tide" : "text-red-700"}>{run.status}</span>
                  {" · "}
                  {run.trigger_entity_type || "n/a"} {run.trigger_entity_id?.slice(0, 8) || ""}
                  {" · "}
                  {new Date(run.created_at).toLocaleString()}
                  {run.error_message ? <span className="block text-xs text-red-700">{run.error_message}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}
