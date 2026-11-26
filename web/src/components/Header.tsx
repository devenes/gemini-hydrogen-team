import { Activity, History, Moon, Sun, Monitor } from "lucide-react";
import type { EnvironmentStatus, ModelProbeResult, RunSummary } from "../types";

export type ThemeChoice = "auto" | "dark" | "light";

interface HeaderProps {
  environment: EnvironmentStatus | null;
  probeResults: ModelProbeResult[];
  runs: RunSummary[];
  activeRunId: string | null;
  onSelectRun: (runId: string) => void;
  onOpenDoctor: () => void;
  theme: ThemeChoice;
  onChangeTheme: (theme: ThemeChoice) => void;
}

export function Header({
  environment,
  probeResults,
  runs,
  activeRunId,
  onSelectRun,
  onOpenDoctor,
  theme,
  onChangeTheme,
}: HeaderProps) {
  const hydrogenProbe = probeResults.find((r) => r.model_id === "gemini-4-hydrogen");
  const authReady = environment && environment.auth_mode !== "unconfigured";

  const nextTheme: Record<ThemeChoice, ThemeChoice> = {
    auto: "dark",
    dark: "light",
    light: "auto",
  };

  return (
    <header className="top-header">
      <div className="brand-group">
        <div className="brand-tile" aria-hidden="true">
          <span className="atomic-num">1</span>
          <span className="atomic-sym">H</span>
        </div>
        <div>
          <h1 className="brand-title">
            Hydrogen Team
            <span className="brand-badge">Gemini 4 • Google ADK</span>
          </h1>
          <p className="brand-subtitle">
            Multi-Agent Collaboration Studio — Orchestrated Rank-Up &amp; Pure Hydrogen Peer Mesh
          </p>
        </div>
      </div>

      <div className="header-actions">
        {runs.length > 0 && (
          <label className="status-pill" aria-label="Switch run history">
            <History size={14} aria-hidden="true" />
            <select
              aria-label="Select previous or active run"
              value={activeRunId ?? ""}
              onChange={(e) => {
                if (e.target.value) onSelectRun(e.target.value);
              }}
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                maxWidth: 190,
                cursor: "pointer",
              }}
            >
              <option value="">New Mission Draft</option>
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.scenario_id} • {r.status} ({r.run_id.slice(-6)})
                </option>
              ))}
            </select>
          </label>
        )}

        <button
          type="button"
          className="status-pill"
          onClick={onOpenDoctor}
          title="Inspect GCP Vertex AI ADC status and probe Gemini 4 models"
        >
          <span
            className={`status-dot ${
              !authReady ? "err" : hydrogenProbe && !hydrogenProbe.available ? "warn" : ""
            }`}
          />
          <Activity size={14} aria-hidden="true" />
          <span>
            {environment?.auth_mode === "vertex_adc"
              ? `Vertex ADC • ${environment.gcp_project ?? "GCP"}`
              : environment?.auth_mode === "gemini_api_key"
              ? "Gemini API Key"
              : "Auth Setup Needed"}
          </span>
        </button>

        <button
          type="button"
          className="btn"
          onClick={() => onChangeTheme(nextTheme[theme])}
          aria-label={`Theme: ${theme}. Click to cycle theme.`}
          title={`Theme: ${theme} (click to switch)`}
        >
          {theme === "dark" ? (
            <Moon size={14} aria-hidden="true" />
          ) : theme === "light" ? (
            <Sun size={14} aria-hidden="true" />
          ) : (
            <Monitor size={14} aria-hidden="true" />
          )}
          <span style={{ textTransform: "capitalize" }}>{theme}</span>
        </button>
      </div>
    </header>
  );
}
