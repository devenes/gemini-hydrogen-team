import { useMemo } from "react";
import { Network } from "lucide-react";
import type {
  AgentBlueprint,
  CollaborationMode,
  ModelSpec,
  RosterMember,
  RunTelemetry,
  TeamEvent,
} from "../types";

interface CollaborationGraphProps {
  mode: CollaborationMode;
  roster: RosterMember[];
  draftAgents: AgentBlueprint[];
  workerModel: ModelSpec | undefined;
  orchestratorModel: ModelSpec | undefined;
  telemetry: RunTelemetry | null;
  events: TeamEvent[];
  selectedAgent: string | null;
  onSelectAgent: (agentName: string | null) => void;
}

interface PositionedNode {
  name: string;
  role: string;
  symbol: string;
  color: string;
  isOrchestrator: boolean;
  status: string;
  x: number;
  y: number;
  tokens: number;
  tools: number;
}

export function CollaborationGraph({
  mode,
  roster,
  draftAgents,
  workerModel,
  orchestratorModel,
  telemetry,
  events,
  selectedAgent,
  onSelectAgent,
}: CollaborationGraphProps) {
  const effectiveRoster: RosterMember[] = useMemo(() => {
    if (roster.length > 0) return roster;
    const wSym = workerModel?.symbol ?? "H";
    const wCol = workerModel?.accent_color ?? "#38bdf8";
    const oSym = orchestratorModel?.symbol ?? "Ne";
    const oCol = orchestratorModel?.accent_color ?? "#f472b6";

    const list: RosterMember[] = [];
    if (mode === "orchestrated") {
      list.push({
        name: "TeamOrchestrator",
        role: `Orchestrator (${oSym})`,
        specialty: "Decomposes tasks & coordinates Hydrogen workers",
        model: orchestratorModel?.id ?? "gemini-4-neon",
        symbol: oSym,
        accent_color: oCol,
        is_orchestrator: true,
        thinking_level: "HIGH",
      });
    }
    draftAgents.forEach((a, idx) => {
      const isCritic = mode === "pipeline_loop" && idx === draftAgents.length - 2 && draftAgents.length >= 3;
      list.push({
        name: a.name,
        role: a.role,
        specialty: a.specialty,
        model: isCritic ? orchestratorModel?.id ?? "gemini-4-neon" : workerModel?.id ?? "gemini-4-hydrogen",
        symbol: isCritic ? oSym : wSym,
        accent_color: isCritic ? oCol : wCol,
        is_orchestrator: false,
        thinking_level: a.thinking_level ?? "MEDIUM",
      });
    });
    return list;
  }, [roster, draftAgents, mode, workerModel, orchestratorModel]);

  const width = 760;
  const height = 270;
  const hubX = width / 2;
  const hubY = height / 2;

  const nodes: PositionedNode[] = useMemo(() => {
    const count = effectiveRoster.length;
    if (count === 0) return [];

    if (mode === "orchestrated") {
      const orch = effectiveRoster.find((m) => m.is_orchestrator) ?? effectiveRoster[0];
      const workers = effectiveRoster.filter((m) => m.name !== orch.name);
      const out: PositionedNode[] = [];
      const orchStat = telemetry?.agents[orch.name];
      out.push({
        name: orch.name,
        role: orch.role,
        symbol: orch.symbol,
        color: orch.accent_color,
        isOrchestrator: true,
        status: orchStat?.status ?? "idle",
        x: hubX,
        y: 66,
        tokens: (orchStat?.prompt_tokens ?? 0) + (orchStat?.output_tokens ?? 0) + (orchStat?.thoughts_tokens ?? 0),
        tools: orchStat?.tool_calls ?? 0,
      });

      const span = Math.min(620, Math.max(260, (workers.length - 1) * 185));
      const startX = hubX - span / 2;
      workers.forEach((w, idx) => {
        const st = telemetry?.agents[w.name];
        const x = workers.length === 1 ? hubX : startX + (idx * span) / (workers.length - 1);
        out.push({
          name: w.name,
          role: w.role,
          symbol: w.symbol,
          color: w.accent_color,
          isOrchestrator: false,
          status: st?.status ?? "idle",
          x,
          y: 205,
          tokens: (st?.prompt_tokens ?? 0) + (st?.output_tokens ?? 0) + (st?.thoughts_tokens ?? 0),
          tools: st?.tool_calls ?? 0,
        });
      });
      return out;
    }

    if (mode === "pipeline_loop") {
      const span = Math.min(620, Math.max(240, (count - 1) * 185));
      const startX = hubX - span / 2;
      return effectiveRoster.map((m, idx) => {
        const st = telemetry?.agents[m.name];
        const x = count === 1 ? hubX : startX + (idx * span) / (count - 1);
        const y = idx >= count - 2 ? 155 : 120;
        return {
          name: m.name,
          role: m.role,
          symbol: m.symbol,
          color: m.accent_color,
          isOrchestrator: false,
          status: st?.status ?? "idle",
          x,
          y,
          tokens: (st?.prompt_tokens ?? 0) + (st?.output_tokens ?? 0) + (st?.thoughts_tokens ?? 0),
          tools: st?.tool_calls ?? 0,
        };
      });
    }

    // Peer Mesh: arrange Hydrogen peers symmetrically around the central shared Team Blackboard!
    const rx = 250;
    const ry = 82;
    return effectiveRoster.map((m, idx) => {
      const angle = (Math.PI * 2 * idx) / count - Math.PI / 2;
      const st = telemetry?.agents[m.name];
      return {
        name: m.name,
        role: m.role,
        symbol: m.symbol,
        color: m.accent_color,
        isOrchestrator: false,
        status: st?.status ?? "idle",
        x: hubX + Math.cos(angle) * rx,
        y: hubY + Math.sin(angle) * ry,
        tokens: (st?.prompt_tokens ?? 0) + (st?.output_tokens ?? 0) + (st?.thoughts_tokens ?? 0),
        tools: st?.tool_calls ?? 0,
      };
    });
  }, [effectiveRoster, mode, telemetry, hubX, hubY]);

  // Identify most recent active communication edges (blackboard posts & handoffs)
  const recentActiveEdges = useMemo(() => {
    const active = new Set<string>();
    const recent = events.slice(-6);
    for (const evt of recent) {
      if (evt.kind === "handoff" && evt.target_agent) {
        active.add(`${evt.agent}->${evt.target_agent}`);
      } else if (evt.kind === "blackboard_post") {
        active.add(`${evt.agent}->blackboard`);
        if (evt.target_agent && evt.target_agent !== "all") {
          active.add(`${evt.agent}->${evt.target_agent}`);
        }
      }
    }
    return active;
  }, [events]);

  const nodeMap = new Map(nodes.map((n) => [n.name, n]));

  return (
    <section className="panel graph-wrap" aria-label="Live multi-agent collaboration topology">
      <div className="panel-header">
        <h2 className="panel-title">
          <Network size={14} aria-hidden="true" />
          Live Collaboration Topology —{" "}
          {mode === "peer_mesh"
            ? "Pure Hydrogen Peer Mesh (No Orchestrator)"
            : mode === "orchestrated"
            ? "Orchestrated Rank-Up Squad"
            : "Assembly Pipeline + Critic Loop"}
        </h2>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {selectedAgent && (
            <button
              type="button"
              className="filter-chip active"
              onClick={() => onSelectAgent(null)}
            >
              Filter: {selectedAgent} ✕
            </button>
          )}
          <span className="count-chip">{telemetry?.phase ?? "Ready to launch"}</span>
        </div>
      </div>

      <svg
        className="graph-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Periodic table multi-agent collaboration graph"
      >
        {/* Topology edges */}
        {mode === "orchestrated" &&
          nodes.slice(1).map((worker) => {
            const orch = nodes[0];
            const key = `${orch.name}->${worker.name}`;
            const isActive =
              recentActiveEdges.has(key) ||
              worker.status === "thinking" ||
              worker.status === "acting";
            return (
              <line
                key={key}
                x1={orch.x}
                y1={orch.y + 24}
                x2={worker.x}
                y2={worker.y - 24}
                className={`graph-edge ${isActive ? "active-beam" : ""}`}
              />
            );
          })}

        {mode === "peer_mesh" && (
          <>
            {nodes.map((n) => {
              const isActive =
                recentActiveEdges.has(`${n.name}->blackboard`) ||
                n.status === "thinking" ||
                n.status === "acting";
              return (
                <line
                  key={`hub-${n.name}`}
                  x1={n.x}
                  y1={n.y}
                  x2={hubX}
                  y2={hubY}
                  className={`graph-edge ${isActive ? "active-beam" : ""}`}
                />
              );
            })}
            {/* Central Shared Team Blackboard node */}
            <g>
              <rect
                x={hubX - 64}
                y={hubY - 22}
                width={128}
                height={44}
                rx={12}
                fill="var(--bg-elevated)"
                stroke="var(--accent-neon)"
                strokeWidth={1.6}
              />
              <text
                x={hubX}
                y={hubY - 3}
                textAnchor="middle"
                fill="var(--accent-neon)"
                fontSize={10}
                fontWeight={800}
                letterSpacing="0.06em"
              >
                BLACKBOARD
              </text>
              <text
                x={hubX}
                y={hubY + 13}
                textAnchor="middle"
                fill="var(--text-secondary)"
                fontSize={10.5}
              >
                {telemetry?.total_blackboard_posts ?? 0} peer posts
              </text>
            </g>
          </>
        )}

        {mode === "pipeline_loop" && (
          <>
            {nodes.slice(0, -1).map((n, idx) => {
              const next = nodes[idx + 1];
              const isActive = n.status === "acting" || next.status === "thinking";
              return (
                <line
                  key={`pipe-${n.name}-${next.name}`}
                  x1={n.x + 28}
                  y1={n.y}
                  x2={next.x - 28}
                  y2={next.y}
                  className={`graph-edge ${isActive ? "active-beam" : ""}`}
                />
              );
            })}
            {nodes.length >= 2 && (
              <path
                d={`M ${nodes[nodes.length - 1].x} ${nodes[nodes.length - 1].y + 30} Q ${(nodes[nodes.length - 1].x + nodes[nodes.length - 2].x) / 2} ${height - 14} ${nodes[nodes.length - 2].x} ${nodes[nodes.length - 2].y + 30}`}
                className="graph-edge"
                stroke="var(--accent-argon)"
              />
            )}
          </>
        )}

        {/* Direct peer-to-peer message arcs */}
        {Array.from(recentActiveEdges).map((edgeKey) => {
          const [fromName, toName] = edgeKey.split("->");
          const from = nodeMap.get(fromName);
          const to = nodeMap.get(toName);
          if (!from || !to || from === to) return null;
          return (
            <line
              key={`direct-${edgeKey}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              className="graph-edge active-beam"
            />
          );
        })}

        {/* Agent Element Nodes */}
        {nodes.map((node) => {
          const isBusy = node.status === "thinking" || node.status === "acting";
          const isSelected = selectedAgent === node.name;
          return (
            <g
              key={node.name}
              className="agent-node"
              transform={`translate(${node.x}, ${node.y})`}
              onClick={() => onSelectAgent(isSelected ? null : node.name)}
              role="button"
              tabIndex={0}
              aria-label={`Filter events by ${node.name} (${node.role}), status ${node.status}`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectAgent(isSelected ? null : node.name);
                }
              }}
            >
              {isBusy && (
                <rect
                  x={-30}
                  y={-30}
                  width={60}
                  height={60}
                  rx={14}
                  fill="none"
                  stroke={node.color}
                  strokeWidth={2.4}
                  className="agent-pulse"
                />
              )}

              <rect
                x={-26}
                y={-26}
                width={52}
                height={52}
                rx={12}
                fill="var(--bg-elevated)"
                stroke={isSelected ? "var(--text-primary)" : node.color}
                strokeWidth={isSelected ? 2.6 : isBusy ? 2.2 : 1.5}
              />

              <text
                x={0}
                y={6}
                textAnchor="middle"
                fill={node.color}
                fontSize={20}
                fontWeight={800}
              >
                {node.symbol}
              </text>

              <text
                x={0}
                y={40}
                textAnchor="middle"
                fill="var(--text-primary)"
                fontSize={11.5}
                fontWeight={700}
              >
                {node.name}
              </text>

              <text
                x={0}
                y={54}
                textAnchor="middle"
                fill={
                  node.status === "done"
                    ? "var(--accent-flash)"
                    : isBusy
                    ? node.color
                    : "var(--text-muted)"
                }
                fontSize={9.5}
                fontWeight={700}
                letterSpacing="0.05em"
              >
                {node.status.toUpperCase()}
                {node.tokens > 0 ? ` • ${(node.tokens / 1000).toFixed(1)}k tok` : ""}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
