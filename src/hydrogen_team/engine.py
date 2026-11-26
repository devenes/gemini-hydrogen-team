"""Run execution engine with Google ADK BasePlugin live telemetry, SSE pub/sub, and run persistence."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal

from google.adk.agents import BaseAgent, RunConfig
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.plugins import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from hydrogen_team.config import Settings, get_settings
from hydrogen_team.events import RunTelemetry, TeamEvent
from hydrogen_team.models import resolve_model_with_fallback
from hydrogen_team.scenarios import AgentBlueprint, CollaborationMode, get_scenario
from hydrogen_team.tools import summarize_tool_result
from hydrogen_team.topologies import build_http_options, build_team_topology
from hydrogen_team.workspace import ArtifactInfo, BlackboardEntry, RunWorkspace

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class RunRequest(BaseModel):
    scenario_id: str = "video_vfx"
    prompt: str = Field(..., min_length=4, max_length=12_000)
    mode: CollaborationMode = "peer_mesh"
    worker_model: str = "gemini-4-hydrogen"
    orchestrator_model: str = "gemini-4-argon"
    worker_thinking_level: str = "MEDIUM"
    orchestrator_thinking_level: str = "HIGH"
    auto_fallback: bool = True
    custom_agents: list[AgentBlueprint] | None = None


class RunSummary(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    prompt: str
    mode: CollaborationMode
    status: RunStatus
    worker_model: str
    orchestrator_model: str
    resolved_worker_model: str
    resolved_orchestrator_model: str
    used_fallback: bool = False
    fallback_reason: str | None = None
    created_at: float
    finished_at: float | None = None
    roster: list[dict[str, Any]] = Field(default_factory=list)
    telemetry: RunTelemetry
    final_output: str = ""
    error: str | None = None


class HydrogenTelemetryPlugin(BasePlugin):
    """ADK Plugin that intercepts EVERY agent, tool, thought, and usage event — including nested AgentTool runs."""

    def __init__(
        self,
        *,
        run_id: str,
        emit_fn: Any,
        telemetry: RunTelemetry,
        agent_models: dict[str, str],
        default_model: str,
    ) -> None:
        super().__init__(name="hydrogen_telemetry")
        self.run_id = run_id
        self.emit_fn = emit_fn
        self.telemetry = telemetry
        self.agent_models = agent_models
        self.default_model = default_model
        self._seen_event_ids: set[str] = set()
        self._last_final_text: str = ""

    @property
    def last_final_text(self) -> str:
        return self._last_final_text

    def _model_for(self, agent_name: str) -> str:
        return self.agent_models.get(agent_name, self.default_model)

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        name = agent.name
        if name in {
            "HydrogenPeerMesh",
            "HydrogenPeerCollective",
            "ParallelDiscoveryPhase",
            "PeerIntegrationPhase",
            "HydrogenPipelineLoop",
            "QualityRefinementLoop",
        }:
            phase_label = {
                "ParallelDiscoveryPhase": "Phase 1 • Parallel Peer Discovery",
                "PeerIntegrationPhase": "Phase 2 • Peer Review & Integration",
                "QualityRefinementLoop": "Quality Gate • Critic & Refiner Loop",
                "HydrogenPeerMesh": "Starting Peer-to-Peer Hydrogen Mesh",
                "HydrogenPipelineLoop": "Starting Assembly Pipeline + Critic Loop",
            }.get(name, name)
            self.telemetry.phase = phase_label
            self.emit_fn(
                TeamEvent(
                    run_id=self.run_id,
                    kind="phase_changed",
                    agent="system",
                    title=phase_label,
                    content=getattr(agent, "description", "") or phase_label,
                )
            )
            return None

        model_id = self._model_for(name)
        ag = self.telemetry.ensure_agent(name, model=model_id)
        ag.status = "thinking"
        ag.last_activity = "Analyzing objective and reasoning..."
        self.emit_fn(
            TeamEvent(
                run_id=self.run_id,
                kind="agent_started",
                agent=name,
                model=model_id,
                title=f"{name} joined the workspace",
                content=getattr(agent, "description", "") or "",
            )
        )
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        name = agent.name
        if name not in self.telemetry.agents:
            return None
        ag = self.telemetry.agents[name]
        if ag.status != "error":
            ag.status = "done"
            ag.last_activity = "Completed contribution"
        self.emit_fn(
            TeamEvent(
                run_id=self.run_id,
                kind="agent_finished",
                agent=name,
                model=ag.model,
                title=f"{name} finished turn",
                content=f"{ag.calls} LLM call(s) • {ag.tool_calls} tool action(s)",
            )
        )
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict[str, Any] | None:
        agent_name = getattr(tool_context, "agent_name", None) or "agent"
        tool_name = getattr(tool, "name", str(tool))
        model_id = self._model_for(agent_name)
        ag = self.telemetry.ensure_agent(agent_name, model=model_id)
        ag.status = "acting"
        ag.tool_calls += 1
        self.telemetry.total_tool_calls += 1

        # Detect orchestrator -> specialist AgentTool delegation for live handoff animation!
        is_delegation = tool_name in self.agent_models
        if is_delegation:
            ag.last_activity = f"Delegating to {tool_name}"
            req_preview = str(tool_args.get("request", tool_args))[:400]
            self.emit_fn(
                TeamEvent(
                    run_id=self.run_id,
                    kind="handoff",
                    agent=agent_name,
                    target_agent=tool_name,
                    model=model_id,
                    title=f"{agent_name} → {tool_name}",
                    content=req_preview,
                    data={"tool": tool_name, "args": _safe_preview_dict(tool_args)},
                )
            )
        else:
            ag.last_activity = f"Calling {tool_name}"
            self.emit_fn(
                TeamEvent(
                    run_id=self.run_id,
                    kind="tool_call",
                    agent=agent_name,
                    model=model_id,
                    title=f"Tool: {tool_name}",
                    content=summarize_tool_result(_safe_preview_dict(tool_args), max_len=420),
                    data={"tool": tool_name, "args": _safe_preview_dict(tool_args)},
                )
            )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        agent_name = getattr(tool_context, "agent_name", None) or "agent"
        tool_name = getattr(tool, "name", str(tool))
        model_id = self._model_for(agent_name)
        ag = self.telemetry.ensure_agent(agent_name, model=model_id)
        ag.status = "thinking"

        self.emit_fn(
            TeamEvent(
                run_id=self.run_id,
                kind="tool_result",
                agent=agent_name,
                target_agent=tool_name if tool_name in self.agent_models else None,
                model=model_id,
                title=f"Result: {tool_name}",
                content=summarize_tool_result(result, max_len=600),
                data={"tool": tool_name},
            )
        )
        return None

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Event | None:
        event_id = getattr(event, "id", None)
        if event_id:
            if event_id in self._seen_event_ids:
                return None
            self._seen_event_ids.add(event_id)

        author = getattr(event, "author", None) or "agent"
        if author == "user":
            return None

        model_id = self._model_for(author)

        # Record exact Gemini token usage & Hydrogen cost telemetry.
        usage = getattr(event, "usage_metadata", None)
        if usage is not None:
            prompt_t = int(getattr(usage, "prompt_token_count", 0) or 0)
            cand_t = int(getattr(usage, "candidates_token_count", 0) or 0)
            thought_t = int(getattr(usage, "thoughts_token_count", 0) or 0)
            if prompt_t or cand_t or thought_t:
                self.telemetry.record_usage(author, model_id, prompt_t, cand_t, thought_t)
                self.emit_fn(
                    TeamEvent(
                        run_id=self.run_id,
                        kind="usage",
                        agent=author,
                        model=model_id,
                        title=f"Usage: {author}",
                        content=f"in={prompt_t} out={cand_t} thought={thought_t}",
                        data=self.telemetry.model_dump(),
                    )
                )

        # Extract native Gemini 4 thinking traces AND visible agent outputs.
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            thought_chunks: list[str] = []
            text_chunks: list[str] = []
            for part in content.parts:
                text = getattr(part, "text", None)
                if not text:
                    continue
                if getattr(part, "thought", False):
                    thought_chunks.append(text)
                else:
                    text_chunks.append(text)

            if thought_chunks:
                merged_thought = "\n".join(thought_chunks).strip()
                if merged_thought:
                    ag = self.telemetry.ensure_agent(author, model=model_id)
                    ag.status = "thinking"
                    ag.last_activity = "Deep reasoning..."
                    self.emit_fn(
                        TeamEvent(
                            run_id=self.run_id,
                            kind="thought",
                            agent=author,
                            model=model_id,
                            title=f"{author} • Internal Reasoning",
                            content=merged_thought,
                        )
                    )

            if text_chunks:
                merged_text = "\n".join(text_chunks).strip()
                if merged_text:
                    self._last_final_text = merged_text
                    self.emit_fn(
                        TeamEvent(
                            run_id=self.run_id,
                            kind="message",
                            agent=author,
                            model=model_id,
                            title=f"{author} response",
                            content=merged_text,
                        )
                    )

        err_msg = getattr(event, "error_message", None)
        if err_msg:
            self.emit_fn(
                TeamEvent(
                    run_id=self.run_id,
                    kind="error",
                    agent=author,
                    model=model_id,
                    title=f"Model error ({author})",
                    content=str(err_msg),
                )
            )
        return None


def _safe_preview_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > 320:
            out[k] = v[:320] + f"… ({len(v)} chars)"
        else:
            out[k] = v
    return out


class ActiveRun:
    """In-memory handle for a single live or completed Hydrogen Team run."""

    def __init__(self, summary: RunSummary, workspace: RunWorkspace) -> None:
        self.summary = summary
        self.workspace = workspace
        self.events: list[TeamEvent] = []
        self._subscribers: set[asyncio.Queue[TeamEvent | None]] = set()
        self.task: asyncio.Task[None] | None = None
        self._seq = 0

    def emit(self, event: TeamEvent) -> None:
        self._seq += 1
        event.seq = self._seq
        if event.kind == "blackboard_post":
            self.summary.telemetry.total_blackboard_posts += 1
            if event.agent in self.summary.telemetry.agents:
                self.summary.telemetry.agents[event.agent].blackboard_posts += 1
        elif event.kind == "artifact_created":
            self.summary.telemetry.total_artifacts = len(self.workspace.list_artifacts())
            if event.agent in self.summary.telemetry.agents:
                self.summary.telemetry.agents[event.agent].artifacts_created += 1

        self.events.append(event)
        self.workspace.append_event_jsonl(event.model_dump())
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def close_streams(self) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> AsyncIterator[TeamEvent]:
        queue: asyncio.Queue[TeamEvent | None] = asyncio.Queue(maxsize=1000)
        # Replay existing events first so late joiners get full live state.
        snapshot = list(self.events)
        self._subscribers.add(queue)
        try:
            for past in snapshot:
                yield past
            if self.summary.status in {"completed", "failed", "cancelled"}:
                return
            while True:
                item = await queue.get()
                if item is None:
                    break
                if item.seq > (snapshot[-1].seq if snapshot else 0):
                    yield item
        finally:
            self._subscribers.discard(queue)


class RunManager:
    """Coordinates Hydrogen Team runs, model fallback resolution, ADK Runners, and persisted run history."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.runs_dir.mkdir(parents=True, exist_ok=True)
        self._runs: dict[str, ActiveRun] = {}
        self._load_existing_runs()

    def _load_existing_runs(self) -> None:
        """Restore completed/previous runs from disk so the UI shows run history across restarts."""
        if not self.settings.runs_dir.exists():
            return
        for meta_file in sorted(self.settings.runs_dir.glob("*/metadata.json"), reverse=True)[:30]:
            try:
                raw = json.loads(meta_file.read_text(encoding="utf-8"))
                summary = RunSummary.model_validate(raw)
                if summary.status in {"queued", "running"}:
                    summary.status = "cancelled"
                ws = RunWorkspace(summary.run_id, self.settings.runs_dir)
                run = ActiveRun(summary, ws)
                if ws.events_file.exists():
                    for line in ws.events_file.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            evt = TeamEvent.model_validate_json(line)
                            run.events.append(evt)
                            run._seq = max(run._seq, evt.seq)
                self._runs[summary.run_id] = run
            except Exception:
                continue

    def list_runs(self) -> list[RunSummary]:
        return sorted(
            (r.summary for r in self._runs.values()),
            key=lambda s: s.created_at,
            reverse=True,
        )

    def get_run(self, run_id: str) -> ActiveRun | None:
        return self._runs.get(run_id)

    def list_artifacts(self, run_id: str) -> list[ArtifactInfo]:
        run = self._runs.get(run_id)
        if not run:
            return []
        return run.workspace.list_artifacts()

    def list_blackboard(self, run_id: str) -> list[BlackboardEntry]:
        run = self._runs.get(run_id)
        if not run:
            return []
        return run.workspace.read_blackboard(limit=100)

    async def start_run(self, request: RunRequest) -> ActiveRun:
        scenario = get_scenario(request.scenario_id)
        run_id = f"{request.scenario_id}-{uuid.uuid4().hex[:8]}"
        workspace = RunWorkspace(run_id, self.settings.runs_dir)
        telemetry = RunTelemetry(run_id=run_id)

        summary = RunSummary(
            run_id=run_id,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            prompt=request.prompt,
            mode=request.mode,
            status="queued",
            worker_model=request.worker_model,
            orchestrator_model=request.orchestrator_model,
            resolved_worker_model=request.worker_model,
            resolved_orchestrator_model=request.orchestrator_model,
            created_at=time.time(),
            telemetry=telemetry,
        )
        active_run = ActiveRun(summary, workspace)
        self._runs[run_id] = active_run
        workspace.save_metadata(summary.model_dump())

        active_run.task = asyncio.create_task(self._execute_run(active_run, request))
        return active_run

    async def cancel_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if not run or not run.task or run.task.done():
            return False
        run.task.cancel()
        run.summary.status = "cancelled"
        run.summary.finished_at = time.time()
        run.summary.telemetry.finished_at = run.summary.finished_at
        run.emit(
            TeamEvent(
                run_id=run_id,
                kind="error",
                agent="system",
                title="Run cancelled by user",
                content="Execution stopped upon user request.",
            )
        )
        run.workspace.save_metadata(run.summary.model_dump())
        run.close_streams()
        return True

    async def _execute_run(self, run: ActiveRun, request: RunRequest) -> None:
        summary = run.summary
        workspace = run.workspace
        scenario = get_scenario(request.scenario_id)

        try:
            self.settings.apply_runtime_env()
            summary.status = "running"
            summary.telemetry.phase = "Verifying Model Availability"

            # Resolve worker & orchestrator models with automatic fallback to Gemini Flash if unavailable.
            worker_res = await resolve_model_with_fallback(
                request.worker_model,
                self.settings,
                auto_fallback=request.auto_fallback,
            )
            orch_res = (
                worker_res
                if request.orchestrator_model == request.worker_model
                else await resolve_model_with_fallback(
                    request.orchestrator_model,
                    self.settings,
                    auto_fallback=request.auto_fallback,
                )
            )
            summary.resolved_worker_model = worker_res.resolved_model
            summary.resolved_orchestrator_model = orch_res.resolved_model

            fallback_reasons: list[str] = []
            if worker_res.used_fallback and worker_res.reason:
                fallback_reasons.append(worker_res.reason)
            if orch_res.used_fallback and orch_res.reason and orch_res.reason not in fallback_reasons:
                fallback_reasons.append(orch_res.reason)
            if fallback_reasons:
                summary.used_fallback = True
                summary.fallback_reason = " ".join(fallback_reasons)
                run.emit(
                    TeamEvent(
                        run_id=summary.run_id,
                        kind="fallback_notice",
                        agent="system",
                        model=summary.resolved_worker_model,
                        title="Automatic Model Fallback Activated",
                        content=summary.fallback_reason,
                    )
                )

            root_agent, roster = build_team_topology(
                scenario=scenario,
                mode=request.mode,
                worker_model=summary.resolved_worker_model,
                orchestrator_model=summary.resolved_orchestrator_model,
                worker_thinking_level=request.worker_thinking_level,
                orchestrator_thinking_level=request.orchestrator_thinking_level,
                workspace=workspace,
                emit=run.emit,
                telemetry=summary.telemetry,
                llm_timeout_ms=self.settings.llm_timeout_ms,
                custom_agents=request.custom_agents,
            )
            summary.roster = roster
            workspace.save_metadata(summary.model_dump())

            run.emit(
                TeamEvent(
                    run_id=summary.run_id,
                    kind="run_started",
                    agent="system",
                    model=summary.resolved_worker_model,
                    title=f"Launched {scenario.name} ({request.mode})",
                    content=request.prompt,
                    data={
                        "mode": request.mode,
                        "roster": roster,
                        "worker_model": summary.resolved_worker_model,
                        "orchestrator_model": summary.resolved_orchestrator_model,
                        "auth_mode": self.settings.auth_mode,
                        "gcp_project": self.settings.resolved_project,
                    },
                )
            )

            agent_models = {member["name"]: member["model"] for member in roster}
            plugin = HydrogenTelemetryPlugin(
                run_id=summary.run_id,
                emit_fn=run.emit,
                telemetry=summary.telemetry,
                agent_models=agent_models,
                default_model=summary.resolved_worker_model,
            )

            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name="hydrogen_team",
                user_id="studio_user",
            )
            runner = Runner(
                app_name="hydrogen_team",
                agent=root_agent,
                session_service=session_service,
                plugins=[plugin],
            )
            run_config_kwargs: dict[str, Any] = {
                "max_llm_calls": self.settings.max_llm_calls,
            }
            if "http_options" in RunConfig.model_fields:
                run_config_kwargs["http_options"] = build_http_options(self.settings.llm_timeout_ms)
            run_config = RunConfig(**run_config_kwargs)

            user_message = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            f"Mission Objective:\n{request.prompt}\n\n"
                            f"Collaboration Mode: {request.mode}\n"
                            f"Scenario: {scenario.name}\n"
                            "Collaborate transparently via the Team Blackboard and save all tangible "
                            "deliverables into the shared workspace."
                        )
                    )
                ],
            )

            async def _drain_runner() -> None:
                async for _event in runner.run_async(
                    user_id="studio_user",
                    session_id=session.id,
                    new_message=user_message,
                    run_config=run_config,
                ):
                    pass

            try:
                await asyncio.wait_for(
                    _drain_runner(),
                    timeout=self.settings.run_timeout_seconds,
                )
            finally:
                await runner.close()

            summary.status = "completed"
            summary.final_output = plugin.last_final_text
            summary.finished_at = time.time()
            summary.telemetry.finished_at = summary.finished_at
            summary.telemetry.phase = "Mission Complete"
            summary.telemetry.total_artifacts = len(workspace.list_artifacts())
            for ag in summary.telemetry.agents.values():
                if ag.status in {"thinking", "acting"}:
                    ag.status = "done"

            run.emit(
                TeamEvent(
                    run_id=summary.run_id,
                    kind="run_completed",
                    agent="system",
                    title="Hydrogen Team mission complete",
                    content=summary.final_output[:1200],
                    data={
                        "telemetry": summary.telemetry.model_dump(),
                        "artifacts": [a.model_dump() for a in workspace.list_artifacts()],
                    },
                )
            )
        except asyncio.CancelledError:
            summary.status = "cancelled"
            summary.finished_at = time.time()
            summary.telemetry.finished_at = summary.finished_at
            raise
        except TimeoutError:
            timeout_msg = (
                f"Run exceeded overall timeout of {self.settings.run_timeout_seconds}s "
                f"(HYDROGEN_RUN_TIMEOUT_SECONDS={self.settings.run_timeout_seconds})."
            )
            summary.status = "failed"
            summary.error = timeout_msg
            summary.finished_at = time.time()
            summary.telemetry.finished_at = summary.finished_at
            summary.telemetry.phase = "Timed Out"
            for ag in summary.telemetry.agents.values():
                if ag.status in {"thinking", "acting"}:
                    ag.status = "error"
                    ag.last_activity = "Timed out"
            run.emit(
                TeamEvent(
                    run_id=summary.run_id,
                    kind="error",
                    agent="system",
                    title=f"Mission timed out after {self.settings.run_timeout_seconds}s",
                    content=timeout_msg,
                )
            )
        except Exception as exc:
            err_text = str(exc) or exc.__class__.__name__
            summary.status = "failed"
            summary.error = err_text
            summary.finished_at = time.time()
            summary.telemetry.finished_at = summary.finished_at
            summary.telemetry.phase = "Failed"
            run.emit(
                TeamEvent(
                    run_id=summary.run_id,
                    kind="error",
                    agent="system",
                    title="Mission failed",
                    content=err_text,
                )
            )
        finally:
            workspace.save_metadata(summary.model_dump())
            run.close_streams()
