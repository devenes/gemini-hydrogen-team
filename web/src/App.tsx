import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, FileCode2, Pin, Terminal, XCircle } from "lucide-react";
import type {
  AgentBlueprint,
  ArtifactInfo,
  BlackboardEntry,
  CollaborationMode,
  EnvironmentStatus,
  ModelProbeResult,
  ModelSpec,
  RunSummary,
  ScenarioSpec,
  TeamEvent,
} from "./types";
import { Header, type ThemeChoice } from "./components/Header";
import { ScenarioSidebar } from "./components/ScenarioSidebar";
import { CollaborationGraph } from "./components/CollaborationGraph";
import { TelemetryBar } from "./components/TelemetryBar";
import { LiveStreamPanel } from "./components/LiveStreamPanel";
import { DeliverablesPanel } from "./components/DeliverablesPanel";
import { DoctorModal } from "./components/DoctorModal";
import { CustomSquadModal } from "./components/CustomSquadModal";
import { SafeMarkdown } from "./components/SafeMarkdown";

type CenterTab = "stream" | "blackboard" | "deliverables";

export default function App() {
  const [environment, setEnvironment] = useState<EnvironmentStatus | null>(null);
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [probeResults, setProbeResults] = useState<ModelProbeResult[]>([]);
  const [probing, setProbing] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioSpec[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);

  // Configuration state
  const [selectedScenarioId, setSelectedScenarioId] = useState("video_vfx");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<CollaborationMode>("peer_mesh");
  const [workerModel, setWorkerModel] = useState("gemini-4-hydrogen");
  const [orchestratorModel, setOrchestratorModel] = useState("gemini-4-neon");
  const [workerThinking, setWorkerThinking] = useState("MEDIUM");
  const [orchestratorThinking, setOrchestratorThinking] = useState("HIGH");
  const [autoFallback, setAutoFallback] = useState(true);
  const [customAgents, setCustomAgents] = useState<AgentBlueprint[] | null>(null);

  // Active run live state
  const [activeRun, setActiveRun] = useState<RunSummary | null>(null);
  const [events, setEvents] = useState<TeamEvent[]>([]);
  const [blackboard, setBlackboard] = useState<BlackboardEntry[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [activeTab, setActiveTab] = useState<CenterTab>("stream");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // UI chrome
  const [doctorOpen, setDoctorOpen] = useState(false);
  const [squadOpen, setSquadOpen] = useState(false);
  const [theme, setTheme] = useState<ThemeChoice>(() => {
    const saved = window.localStorage.getItem("hydrogen_theme");
    return saved === "dark" || saved === "light" || saved === "auto" ? saved : "dark";
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // Apply color-scheme theme attribute on `:root`
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "auto") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    window.localStorage.setItem("hydrogen_theme", theme);
  }, [theme]);

  const refreshRunsList = useCallback(async () => {
    const res = await fetch("/api/runs");
    if (res.ok) {
      const data = await res.json();
      setRuns(data.runs ?? []);
    }
  }, []);

  const probeModels = useCallback(async (force = false) => {
    setProbing(true);
    try {
      const res = await fetch(`/api/models/probe?force=${force ? "true" : "false"}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setProbeResults(data.results ?? []);
        if (data.environment) setEnvironment(data.environment);
      }
    } finally {
      setProbing(false);
    }
  }, []);

  // Bootstrap initial metadata
  useEffect(() => {
    async function boot() {
      const [hRes, mRes, sRes, rRes] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/models"),
        fetch("/api/scenarios"),
        fetch("/api/runs"),
      ]);
      if (hRes.ok) {
        const hData = await hRes.json();
        setEnvironment(hData.environment);
      }
      if (mRes.ok) {
        const mData = await mRes.json();
        setModels(mData.models ?? []);
        if (mData.defaults?.worker_model) setWorkerModel(mData.defaults.worker_model);
        if (mData.defaults?.orchestrator_model) setOrchestratorModel(mData.defaults.orchestrator_model);
      }
      if (sRes.ok) {
        const sData = await sRes.json();
        const scList: ScenarioSpec[] = sData.scenarios ?? [];
        setScenarios(scList);
        if (scList.length > 0) {
          const first = scList[0];
          setSelectedScenarioId(first.id);
          setMode(first.recommended_mode);
          setOrchestratorModel(first.recommended_orchestrator);
          if (first.templates[0]) {
            setSelectedTemplateId(first.templates[0].id);
            setPrompt(first.templates[0].prompt);
          }
        }
      }
      if (rRes.ok) {
        const rData = await rRes.json();
        setRuns(rData.runs ?? []);
      }
    }
    void boot();
  }, []);

  const connectStream = useCallback(
    (runId: string) => {
      eventSourceRef.current?.close();
      const es = new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream`);
      eventSourceRef.current = es;

      const handleEvent = (raw: MessageEvent) => {
        try {
          const evt: TeamEvent = JSON.parse(raw.data);
          setEvents((prev) => {
            if (prev.some((e) => e.seq === evt.seq)) return prev;
            return [...prev, evt];
          });

          if (evt.kind === "run_started" && evt.data.roster) {
            setActiveRun((prev) =>
              prev
                ? {
                    ...prev,
                    status: "running",
                    roster: evt.data.roster as RunSummary["roster"],
                    resolved_worker_model:
                      (evt.data.worker_model as string) ?? prev.resolved_worker_model,
                    resolved_orchestrator_model:
                      (evt.data.orchestrator_model as string) ?? prev.resolved_orchestrator_model,
                  }
                : prev
            );
          } else if (evt.kind === "fallback_notice") {
            setActiveRun((prev) =>
              prev
                ? { ...prev, used_fallback: true, fallback_reason: evt.content }
                : prev
            );
          } else if (evt.kind === "phase_changed") {
            setActiveRun((prev) =>
              prev
                ? { ...prev, telemetry: { ...prev.telemetry, phase: evt.title } }
                : prev
            );
          } else if (evt.kind === "agent_started" || evt.kind === "agent_finished" || evt.kind === "tool_call" || evt.kind === "thought") {
            setActiveRun((prev) => {
              if (!prev) return prev;
              const existing = prev.telemetry.agents[evt.agent];
              if (!existing) return prev;
              const nextStatus =
                evt.kind === "agent_finished"
                  ? "done"
                  : evt.kind === "tool_call"
                  ? "acting"
                  : "thinking";
              return {
                ...prev,
                telemetry: {
                  ...prev.telemetry,
                  total_tool_calls:
                    evt.kind === "tool_call"
                      ? prev.telemetry.total_tool_calls + 1
                      : prev.telemetry.total_tool_calls,
                  agents: {
                    ...prev.telemetry.agents,
                    [evt.agent]: {
                      ...existing,
                      status: nextStatus,
                    },
                  },
                },
              };
            });
          } else if (evt.kind === "usage" && evt.data) {
            setActiveRun((prev) =>
              prev ? { ...prev, telemetry: evt.data as unknown as RunSummary["telemetry"] } : prev
            );
          } else if (evt.kind === "blackboard_post" && evt.data) {
            const entry = evt.data as unknown as BlackboardEntry;
            setBlackboard((prev) =>
              prev.some((b) => b.seq === entry.seq) ? prev : [...prev, entry]
            );
            setActiveRun((prev) =>
              prev
                ? {
                    ...prev,
                    telemetry: {
                      ...prev.telemetry,
                      total_blackboard_posts: prev.telemetry.total_blackboard_posts + 1,
                    },
                  }
                : prev
            );
          } else if (evt.kind === "artifact_created" && evt.data) {
            const art = evt.data as unknown as ArtifactInfo;
            setArtifacts((prev) => {
              const filtered = prev.filter((a) => a.path !== art.path);
              return [...filtered, art];
            });
            setActiveRun((prev) =>
              prev
                ? {
                    ...prev,
                    telemetry: {
                      ...prev.telemetry,
                      total_artifacts: Math.max(prev.telemetry.total_artifacts, 1),
                    },
                  }
                : prev
            );
          } else if (evt.kind === "run_completed") {
            void fetch(`/api/runs/${encodeURIComponent(runId)}`)
              .then((r) => r.json())
              .then((detail) => {
                setActiveRun(detail.summary);
                setBlackboard(detail.blackboard ?? []);
                setArtifacts(detail.artifacts ?? []);
                void refreshRunsList();
              });
          } else if (evt.kind === "error" && evt.agent === "system") {
            setActiveRun((prev) =>
              prev
                ? { ...prev, status: "failed", error: evt.content, finished_at: Date.now() / 1000 }
                : prev
            );
            void refreshRunsList();
          }
        } catch {
          // ignore malformed SSE chunk
        }
      };

      const eventKinds = [
        "run_started",
        "phase_changed",
        "agent_started",
        "agent_finished",
        "thought",
        "message",
        "tool_call",
        "tool_result",
        "blackboard_post",
        "artifact_created",
        "handoff",
        "usage",
        "fallback_notice",
        "run_completed",
        "error",
      ];
      eventKinds.forEach((k) => es.addEventListener(k, handleEvent));
      es.addEventListener("stream_end", () => {
        es.close();
        void refreshRunsList();
      });
      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          void refreshRunsList();
        }
      };
    },
    [refreshRunsList]
  );

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const handleSelectScenario = (scenarioId: string) => {
    setSelectedScenarioId(scenarioId);
    setCustomAgents(null);
    const sc = scenarios.find((s) => s.id === scenarioId);
    if (sc) {
      setMode(sc.recommended_mode);
      setOrchestratorModel(sc.recommended_orchestrator);
      if (sc.templates[0]) {
        setSelectedTemplateId(sc.templates[0].id);
        setPrompt(sc.templates[0].prompt);
      }
    }
  };

  const handleSelectRun = async (runId: string) => {
    eventSourceRef.current?.close();
    const res = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
    if (!res.ok) return;
    const detail = await res.json();
    setActiveRun(detail.summary);
    setEvents(detail.events ?? []);
    setBlackboard(detail.blackboard ?? []);
    setArtifacts(detail.artifacts ?? []);
    setSelectedAgent(null);
    if (detail.summary.status === "running" || detail.summary.status === "queued") {
      connectStream(runId);
    }
  };

  const handleLaunch = async () => {
    eventSourceRef.current?.close();
    setEvents([]);
    setBlackboard([]);
    setArtifacts([]);
    setSelectedAgent(null);
    setActiveTab("stream");

    const res = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_id: selectedScenarioId,
        prompt,
        mode,
        worker_model: workerModel,
        orchestrator_model: orchestratorModel,
        worker_thinking_level: workerThinking,
        orchestrator_thinking_level: orchestratorThinking,
        auto_fallback: autoFallback,
        custom_agents: customAgents,
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      alert(`Failed to launch run: ${err}`);
      return;
    }
    const summary: RunSummary = await res.json();
    setActiveRun(summary);
    void refreshRunsList();
    connectStream(summary.run_id);
  };

  const handleCancel = async () => {
    if (!activeRun) return;
    await fetch(`/api/runs/${encodeURIComponent(activeRun.run_id)}/cancel`, {
      method: "POST",
    });
    eventSourceRef.current?.close();
    await handleSelectRun(activeRun.run_id);
  };

  const activeScenario = scenarios.find((s) => s.id === selectedScenarioId) ?? scenarios[0];
  const isRunning = activeRun?.status === "running" || activeRun?.status === "queued";

  return (
    <div className="app-shell">
      <Header
        environment={environment}
        probeResults={probeResults}
        runs={runs}
        activeRunId={activeRun?.run_id ?? null}
        onSelectRun={handleSelectRun}
        onOpenDoctor={() => {
          setDoctorOpen(true);
          if (probeResults.length === 0) void probeModels(false);
        }}
        theme={theme}
        onChangeTheme={setTheme}
      />

      <main className="workspace-grid">
        <ScenarioSidebar
          scenarios={scenarios}
          models={models}
          selectedScenarioId={selectedScenarioId}
          selectedTemplateId={selectedTemplateId}
          prompt={prompt}
          mode={mode}
          workerModel={workerModel}
          orchestratorModel={orchestratorModel}
          workerThinking={workerThinking}
          orchestratorThinking={orchestratorThinking}
          autoFallback={autoFallback}
          customAgents={customAgents}
          isRunning={isRunning}
          onSelectScenario={handleSelectScenario}
          onSelectTemplate={(id, p) => {
            setSelectedTemplateId(id);
            setPrompt(p);
          }}
          onPromptChange={(p) => {
            setPrompt(p);
            setSelectedTemplateId(null);
          }}
          onModeChange={setMode}
          onWorkerModelChange={setWorkerModel}
          onOrchestratorModelChange={setOrchestratorModel}
          onWorkerThinkingChange={setWorkerThinking}
          onOrchestratorThinkingChange={setOrchestratorThinking}
          onAutoFallbackChange={setAutoFallback}
          onOpenCustomSquad={() => setSquadOpen(true)}
          onLaunch={() => void handleLaunch()}
          onCancel={() => void handleCancel()}
        />

        <div className="main-column">
          {activeRun?.used_fallback && activeRun.fallback_reason && (
            <div className="banner-warning" role="status">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>{activeRun.fallback_reason}</span>
            </div>
          )}

          {activeRun?.status === "failed" && activeRun.error && (
            <div className="banner-error" role="alert">
              <XCircle size={16} aria-hidden="true" />
              <div className="banner-error-body">
                <strong>Run failed:</strong> <span>{activeRun.error}</span>
              </div>
            </div>
          )}

          <TelemetryBar run={activeRun} />

          <CollaborationGraph
            mode={activeRun?.mode ?? mode}
            roster={activeRun?.roster ?? []}
            draftAgents={customAgents ?? activeScenario?.agents ?? []}
            workerModel={models.find((m) => m.id === (activeRun?.resolved_worker_model ?? workerModel))}
            orchestratorModel={models.find(
              (m) => m.id === (activeRun?.resolved_orchestrator_model ?? orchestratorModel)
            )}
            telemetry={activeRun?.telemetry ?? null}
            events={events}
            selectedAgent={selectedAgent}
            onSelectAgent={setSelectedAgent}
          />

          <section className="panel" aria-label="Live activity and deliverables">
            <div className="tabs-bar">
              <div className="tab-group" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "stream"}
                  className={`tab-btn ${activeTab === "stream" ? "active" : ""}`}
                  onClick={() => setActiveTab("stream")}
                >
                  <Terminal size={14} aria-hidden="true" />
                  Live Stream
                  <span className="count-chip">
                    {events.filter((e) => e.kind !== "usage").length}
                  </span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "blackboard"}
                  className={`tab-btn ${activeTab === "blackboard" ? "active" : ""}`}
                  onClick={() => setActiveTab("blackboard")}
                >
                  <Pin size={14} aria-hidden="true" />
                  Team Blackboard
                  <span className="count-chip">{blackboard.length}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "deliverables"}
                  className={`tab-btn ${activeTab === "deliverables" ? "active" : ""}`}
                  onClick={() => setActiveTab("deliverables")}
                >
                  <FileCode2 size={14} aria-hidden="true" />
                  Deliverables &amp; Preview
                  <span className="count-chip">{artifacts.length}</span>
                </button>
              </div>
            </div>

            {activeTab === "stream" && (
              <LiveStreamPanel events={events} selectedAgent={selectedAgent} />
            )}

            {activeTab === "blackboard" && (
              <div className="stream-list">
                {blackboard.length === 0 ? (
                  <div className="empty-state">
                    <Pin size={26} aria-hidden="true" />
                    <strong>Team Blackboard is empty</strong>
                    <p style={{ margin: 0 }}>
                      Proposals, peer critiques, handoffs, and consensus decisions shared among
                      Hydrogen agents appear here in real time.
                    </p>
                  </div>
                ) : (
                  blackboard.map((b) => (
                    <article key={b.seq} className="event-card kind-blackboard_post">
                      <div className="event-head">
                        <div className="event-meta">
                          <span className="agent-badge">
                            #{b.seq} {b.author} → {b.to_agent}
                          </span>
                          <span className="event-title">
                            [{b.kind.toUpperCase()}] {b.topic}
                          </span>
                        </div>
                      </div>
                      <SafeMarkdown content={b.message} />
                    </article>
                  ))
                )}
              </div>
            )}

            {activeTab === "deliverables" && (
              <DeliverablesPanel runId={activeRun?.run_id ?? null} artifacts={artifacts} />
            )}
          </section>
        </div>
      </main>

      <DoctorModal
        open={doctorOpen}
        environment={environment}
        models={models}
        probeResults={probeResults}
        probing={probing}
        onProbe={(force) => void probeModels(force)}
        onClose={() => setDoctorOpen(false)}
      />

      {activeScenario && (
        <CustomSquadModal
          open={squadOpen}
          defaultAgents={activeScenario.agents}
          customAgents={customAgents}
          onSave={setCustomAgents}
          onClose={() => setSquadOpen(false)}
        />
      )}
    </div>
  );
}
