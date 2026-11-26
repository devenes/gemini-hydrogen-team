import { useEffect, useRef, useState } from "react";
import { Brain, FileCheck2, MessageSquare, Pin, Wrench, Zap, AlertTriangle } from "lucide-react";
import type { TeamEvent } from "../types";
import { SafeMarkdown } from "./SafeMarkdown";

interface LiveStreamPanelProps {
  events: TeamEvent[];
  selectedAgent: string | null;
}

type StreamFilter = "all" | "thought" | "blackboard" | "tools" | "outputs";

function formatClock(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function LiveStreamPanel({ events, selectedAgent }: LiveStreamPanelProps) {
  const [filter, setFilter] = useState<StreamFilter>("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const visibleEvents = events.filter((e) => {
    if (e.kind === "usage") return false;
    if (selectedAgent && e.agent !== selectedAgent && e.target_agent !== selectedAgent) {
      return false;
    }
    if (filter === "thought") return e.kind === "thought";
    if (filter === "blackboard") return e.kind === "blackboard_post" || e.kind === "handoff";
    if (filter === "tools") return e.kind === "tool_call" || e.kind === "tool_result" || e.kind === "artifact_created";
    if (filter === "outputs") return e.kind === "message" || e.kind === "run_completed";
    return true;
  });

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [visibleEvents.length, autoScroll]);

  return (
    <div>
      <div
        style={{
          padding: "10px 16px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div className="filter-row" role="group" aria-label="Filter stream events">
          {(
            [
              ["all", "All Events"],
              ["thought", "Thinking Traces"],
              ["blackboard", "Peer Collaboration"],
              ["tools", "Tools & Artifacts"],
              ["outputs", "Agent Outputs"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={`filter-chip ${filter === key ? "active" : ""}`}
              onClick={() => setFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="checkbox-row" style={{ fontSize: 11.5 }}>
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>
      </div>

      <div className="stream-list" role="log" aria-live="polite" aria-label="Live agent activity log">
        {visibleEvents.length === 0 ? (
          <div className="empty-state">
            <Brain size={28} aria-hidden="true" />
            <strong>Waiting for Hydrogen Team telemetry</strong>
            <p style={{ margin: 0, maxWidth: 420 }}>
              Pick a scenario template on the left — like Code-First Video &amp; VFX Studio, Software
              Engineering, Company Monetization, or Trip Planning — and click Launch Hydrogen Team.
            </p>
          </div>
        ) : (
          visibleEvents.map((evt) => (
            <article key={`${evt.run_id}-${evt.seq}`} className={`event-card kind-${evt.kind}`}>
              <div className="event-head">
                <div className="event-meta">
                  <span className="agent-badge">
                    {evt.kind === "thought" && <Brain size={12} aria-hidden="true" />}
                    {evt.kind === "blackboard_post" && <Pin size={12} aria-hidden="true" />}
                    {evt.kind === "handoff" && <Zap size={12} aria-hidden="true" />}
                    {(evt.kind === "tool_call" || evt.kind === "tool_result") && (
                      <Wrench size={12} aria-hidden="true" />
                    )}
                    {evt.kind === "artifact_created" && <FileCheck2 size={12} aria-hidden="true" />}
                    {evt.kind === "message" && <MessageSquare size={12} aria-hidden="true" />}
                    {(evt.kind === "error" || evt.kind === "fallback_notice") && (
                      <AlertTriangle size={12} aria-hidden="true" />
                    )}
                    {evt.agent}
                    {evt.target_agent ? ` → ${evt.target_agent}` : ""}
                  </span>
                  <span className="event-title">{evt.title}</span>
                  {evt.model && (
                    <span className="count-chip" style={{ fontFamily: "var(--font-mono)" }}>
                      {evt.model}
                    </span>
                  )}
                </div>
                <span className="event-time">{formatClock(evt.timestamp)}</span>
              </div>

              {evt.kind === "thought" ? (
                <details className="thought-details" open={evt.content.length < 600}>
                  <summary>View Gemini 4 Reasoning Trace ({evt.content.length} chars)</summary>
                  <div className="thought-body">{evt.content}</div>
                </details>
              ) : evt.kind === "tool_call" || evt.kind === "tool_result" ? (
                <pre className="code-snippet">{evt.content}</pre>
              ) : evt.kind === "message" || evt.kind === "blackboard_post" ? (
                <SafeMarkdown content={evt.content} />
              ) : (
                evt.content && (
                  <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-secondary)" }}>
                    {evt.content}
                  </p>
                )
              )}
            </article>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
