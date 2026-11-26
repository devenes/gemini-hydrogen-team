import { useEffect, useState } from "react";
import type { RunSummary } from "../types";

interface TelemetryBarProps {
  run: RunSummary | null;
}

export function TelemetryBar({ run }: TelemetryBarProps) {
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    if (!run || (run.status !== "running" && run.status !== "queued")) return;
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(timer);
  }, [run]);

  const t = run?.telemetry;
  const elapsedSec = run
    ? Math.max(0, Math.round((run.finished_at ?? now) - run.created_at))
    : 0;
  const mins = Math.floor(elapsedSec / 60);
  const secs = elapsedSec % 60;
  const elapsedLabel = run ? `${mins}:${secs.toString().padStart(2, "0")}` : "0:00";

  return (
    <section className="telemetry-bar" aria-label="Live mission telemetry" aria-live="polite">
      <div className="metric-card">
        <span className="metric-label">Status</span>
        <span className="metric-value" style={{ textTransform: "capitalize" }}>
          {run?.status ?? "Idle"}
        </span>
        <span className="metric-sub">Elapsed {elapsedLabel}</span>
      </div>

      <div className="metric-card">
        <span className="metric-label">Total Tokens</span>
        <span className="metric-value">{(t?.total_tokens ?? 0).toLocaleString()}</span>
        <span className="metric-sub">
          Thoughts: {(t?.total_thoughts_tokens ?? 0).toLocaleString()}
        </span>
      </div>

      <div className="metric-card">
        <span className="metric-label">Estimated Cost</span>
        <span className="metric-value">${(t?.total_cost_usd ?? 0).toFixed(4)}</span>
        <span className="metric-sub">
          Workers: {run?.resolved_worker_model ?? "gemini-4-hydrogen"}
        </span>
      </div>

      <div className="metric-card savings">
        <span className="metric-label">Hydrogen Savings</span>
        <span className="metric-value">
          ${(t?.estimated_savings_vs_neon_usd ?? 0).toFixed(4)}
        </span>
        <span className="metric-sub">Saved vs all-Neon squad</span>
      </div>

      <div className="metric-card">
        <span className="metric-label">Collaboration</span>
        <span className="metric-value">
          {t?.total_blackboard_posts ?? 0} posts • {t?.total_tool_calls ?? 0} tools
        </span>
        <span className="metric-sub">{t?.total_artifacts ?? 0} deliverables saved</span>
      </div>
    </section>
  );
}
