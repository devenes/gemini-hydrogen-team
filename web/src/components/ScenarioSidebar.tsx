import {
  Briefcase,
  Code2,
  Compass,
  Film,
  Microscope,
  Play,
  Rocket,
  SlidersHorizontal,
  Sparkles,
  Square,
  Users,
} from "lucide-react";
import type {
  AgentBlueprint,
  CollaborationMode,
  ModelSpec,
  ScenarioSpec,
} from "../types";

interface ScenarioSidebarProps {
  scenarios: ScenarioSpec[];
  models: ModelSpec[];
  selectedScenarioId: string;
  selectedTemplateId: string | null;
  prompt: string;
  mode: CollaborationMode;
  workerModel: string;
  orchestratorModel: string;
  workerThinking: string;
  orchestratorThinking: string;
  autoFallback: boolean;
  customAgents: AgentBlueprint[] | null;
  isRunning: boolean;
  onSelectScenario: (scenarioId: string) => void;
  onSelectTemplate: (templateId: string, prompt: string) => void;
  onPromptChange: (prompt: string) => void;
  onModeChange: (mode: CollaborationMode) => void;
  onWorkerModelChange: (modelId: string) => void;
  onOrchestratorModelChange: (modelId: string) => void;
  onWorkerThinkingChange: (level: string) => void;
  onOrchestratorThinkingChange: (level: string) => void;
  onAutoFallbackChange: (enabled: boolean) => void;
  onOpenCustomSquad: () => void;
  onLaunch: () => void;
  onCancel: () => void;
}

function ScenarioIcon({ name }: { name: string }) {
  switch (name) {
    case "film":
      return <Film size={16} aria-hidden="true" />;
    case "code":
      return <Code2 size={16} aria-hidden="true" />;
    case "briefcase":
      return <Briefcase size={16} aria-hidden="true" />;
    case "microscope":
      return <Microscope size={16} aria-hidden="true" />;
    case "compass":
      return <Compass size={16} aria-hidden="true" />;
    case "rocket":
      return <Rocket size={16} aria-hidden="true" />;
    default:
      return <Sparkles size={16} aria-hidden="true" />;
  }
}

export function ScenarioSidebar({
  scenarios,
  models,
  selectedScenarioId,
  selectedTemplateId,
  prompt,
  mode,
  workerModel,
  orchestratorModel,
  workerThinking,
  orchestratorThinking,
  autoFallback,
  customAgents,
  isRunning,
  onSelectScenario,
  onSelectTemplate,
  onPromptChange,
  onModeChange,
  onWorkerModelChange,
  onOrchestratorModelChange,
  onWorkerThinkingChange,
  onOrchestratorThinkingChange,
  onAutoFallbackChange,
  onOpenCustomSquad,
  onLaunch,
  onCancel,
}: ScenarioSidebarProps) {
  const activeScenario = scenarios.find((s) => s.id === selectedScenarioId) ?? scenarios[0];
  const workerSpec = models.find((m) => m.id === workerModel);
  const orchSpec = models.find((m) => m.id === orchestratorModel);
  const effectiveAgents = customAgents ?? activeScenario?.agents ?? [];

  return (
    <aside className="sidebar-stack" aria-label="Mission configuration">
      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <Sparkles size={14} aria-hidden="true" />
            1. Choose Scenario
          </h2>
          <span className="count-chip">{scenarios.length} studios</span>
        </div>
        <div className="panel-body">
          <div className="scenario-grid">
            {scenarios.map((sc) => (
              <button
                key={sc.id}
                type="button"
                className={`scenario-card ${sc.id === selectedScenarioId ? "active" : ""}`}
                onClick={() => onSelectScenario(sc.id)}
              >
                <div className="scenario-card-head">
                  <ScenarioIcon name={sc.icon} />
                  <span className="scenario-cat">{sc.category}</span>
                </div>
                <span className="scenario-name">{sc.name}</span>
              </button>
            ))}
          </div>
          {activeScenario && (
            <p style={{ margin: "10px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
              {activeScenario.tagline}
            </p>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">2. Prompt Template &amp; Mission</h2>
        </div>
        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {activeScenario && (
            <div className="template-list">
              {activeScenario.templates.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`template-btn ${selectedTemplateId === t.id ? "selected" : ""}`}
                  onClick={() => onSelectTemplate(t.id, t.prompt)}
                >
                  <span>{t.title}</span>
                  <span className="template-badge">{t.badge}</span>
                </button>
              ))}
            </div>
          )}

          <div>
            <label htmlFor="mission-prompt" className="field-label">
              <span>Mission Objective</span>
              <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>Editable</span>
            </label>
            <textarea
              id="mission-prompt"
              className="prompt-input"
              required
              minLength={4}
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              placeholder="Describe what you want your Hydrogen Team to design, code, model, plan, or render..."
            />
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <SlidersHorizontal size={14} aria-hidden="true" />
            3. Collaboration &amp; Models
          </h2>
          <button
            type="button"
            className="btn"
            style={{ padding: "4px 9px", fontSize: 11.5 }}
            onClick={onOpenCustomSquad}
          >
            <Users size={13} aria-hidden="true" />
            Squad ({effectiveAgents.length})
          </button>
        </div>

        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <span className="field-label">Collaboration Topology</span>
            <div className="mode-pills" role="group" aria-label="Collaboration topology">
              <button
                type="button"
                className={`mode-pill ${mode === "peer_mesh" ? "active" : ""}`}
                onClick={() => onModeChange("peer_mesh")}
              >
                <strong>Peer Mesh</strong>
                <span>No Orchestrator</span>
              </button>
              <button
                type="button"
                className={`mode-pill ${mode === "orchestrated" ? "active" : ""}`}
                onClick={() => onModeChange("orchestrated")}
              >
                <strong>Rank-Up Lead</strong>
                <span>Orchestrated</span>
              </button>
              <button
                type="button"
                className={`mode-pill ${mode === "pipeline_loop" ? "active" : ""}`}
                onClick={() => onModeChange("pipeline_loop")}
              >
                <strong>Critic Loop</strong>
                <span>Pipeline + QA</span>
              </button>
            </div>
          </div>

          <div className="two-col">
            <div>
              <label htmlFor="worker-model" className="field-label">
                Specialist Model
              </label>
              <select
                id="worker-model"
                className="select-input"
                value={workerModel}
                onChange={(e) => onWorkerModelChange(e.target.value)}
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    [{m.symbol}] {m.display_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="worker-thinking" className="field-label">
                Worker Thinking
              </label>
              <select
                id="worker-thinking"
                className="select-input"
                value={workerThinking}
                onChange={(e) => onWorkerThinkingChange(e.target.value)}
              >
                {(workerSpec?.thinking_levels ?? ["LOW", "MEDIUM", "HIGH"]).map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {lvl}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {mode !== "peer_mesh" && (
            <div className="two-col">
              <div>
                <label htmlFor="orch-model" className="field-label">
                  {mode === "orchestrated" ? "Orchestrator Model" : "Critic Model"}
                </label>
                <select
                  id="orch-model"
                  className="select-input"
                  value={orchestratorModel}
                  onChange={(e) => onOrchestratorModelChange(e.target.value)}
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      [{m.symbol}] {m.display_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="orch-thinking" className="field-label">
                  Lead Thinking
                </label>
                <select
                  id="orch-thinking"
                  className="select-input"
                  value={orchestratorThinking}
                  onChange={(e) => onOrchestratorThinkingChange(e.target.value)}
                >
                  {(orchSpec?.thinking_levels ?? ["LOW", "MEDIUM", "HIGH"]).map((lvl) => (
                    <option key={lvl} value={lvl}>
                      {lvl}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={autoFallback}
              onChange={(e) => onAutoFallbackChange(e.target.checked)}
            />
            <span>Auto-fallback to Gemini 2.5 Flash if Hydrogen is unavailable</span>
          </label>

          {isRunning ? (
            <button type="button" className="btn btn-danger launch-btn" onClick={onCancel}>
              <Square size={15} aria-hidden="true" />
              Stop Active Mission
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary launch-btn"
              disabled={!prompt.trim()}
              onClick={onLaunch}
            >
              <Play size={16} aria-hidden="true" />
              Launch Hydrogen Team
            </button>
          )}
        </div>
      </section>
    </aside>
  );
}
