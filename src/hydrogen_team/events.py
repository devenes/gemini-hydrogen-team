"""Structured telemetry events and cost accounting for multi-agent runs."""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from hydrogen_team.models import estimate_cost_usd, estimate_flagship_savings_usd, get_model_spec

EventKind = Literal[
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
]


class TeamEvent(BaseModel):
    """Atomic event emitted during a Hydrogen Team collaboration run."""

    seq: int = 0
    run_id: str
    timestamp: float = Field(default_factory=time.time)
    kind: EventKind
    agent: str = "system"
    target_agent: str | None = None
    model: str | None = None
    title: str = ""
    content: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class AgentTelemetry(BaseModel):
    name: str
    role: str = ""
    model: str = "gemini-4-hydrogen"
    symbol: str = "H"
    accent_color: str = "#38bdf8"
    is_orchestrator: bool = False
    status: Literal["idle", "thinking", "acting", "done", "error"] = "idle"
    calls: int = 0
    tool_calls: int = 0
    blackboard_posts: int = 0
    artifacts_created: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0
    cost_usd: float = 0.0
    last_activity: str = ""


class RunTelemetry(BaseModel):
    run_id: str
    started_at: float = Field(default_factory=time.time)
    finished_at: float | None = None
    phase: str = "Initializing"
    total_prompt_tokens: int = 0
    total_output_tokens: int = 0
    total_thoughts_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    estimated_savings_vs_neon_usd: float = 0.0
    total_tool_calls: int = 0
    total_blackboard_posts: int = 0
    total_artifacts: int = 0
    agents: dict[str, AgentTelemetry] = Field(default_factory=dict)

    def ensure_agent(
        self,
        name: str,
        *,
        role: str = "",
        model: str = "gemini-4-hydrogen",
        is_orchestrator: bool = False,
    ) -> AgentTelemetry:
        if name not in self.agents:
            spec = get_model_spec(model)
            self.agents[name] = AgentTelemetry(
                name=name,
                role=role,
                model=model,
                symbol=spec.symbol,
                accent_color=spec.accent_color,
                is_orchestrator=is_orchestrator,
            )
        return self.agents[name]

    def record_usage(
        self,
        agent_name: str,
        model_id: str,
        prompt_tokens: int,
        output_tokens: int,
        thoughts_tokens: int,
    ) -> AgentTelemetry:
        agent = self.ensure_agent(agent_name, model=model_id)
        agent.calls += 1
        agent.prompt_tokens += max(prompt_tokens, 0)
        agent.output_tokens += max(output_tokens, 0)
        agent.thoughts_tokens += max(thoughts_tokens, 0)
        delta_cost = estimate_cost_usd(model_id, prompt_tokens, output_tokens, thoughts_tokens)
        agent.cost_usd = round(agent.cost_usd + delta_cost, 6)

        self.total_prompt_tokens += max(prompt_tokens, 0)
        self.total_output_tokens += max(output_tokens, 0)
        self.total_thoughts_tokens += max(thoughts_tokens, 0)
        self.total_tokens = (
            self.total_prompt_tokens + self.total_output_tokens + self.total_thoughts_tokens
        )
        self.total_cost_usd = round(self.total_cost_usd + delta_cost, 6)
        self.estimated_savings_vs_neon_usd = estimate_flagship_savings_usd(
            self.total_cost_usd,
            self.total_prompt_tokens,
            self.total_output_tokens,
            self.total_thoughts_tokens,
            baseline_model_id="gemini-4-neon",
        )
        return agent
