"""Google ADK multi-agent topology builders: Orchestrated Rank-Up, Peer Mesh (No Orchestrator), and Pipeline + Critic Loop."""

from __future__ import annotations

import warnings
from typing import Any

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import AgentTool, exit_loop
from google.genai import types

from hydrogen_team.events import RunTelemetry
from hydrogen_team.models import get_model_spec
from hydrogen_team.scenarios import AgentBlueprint, CollaborationMode, ScenarioSpec
from hydrogen_team.tools import EventCallback, create_workspace_toolset
from hydrogen_team.workspace import RunWorkspace


def build_thinking_planner(
    model_id: str,
    thinking_level: str = "MEDIUM",
    *,
    include_thoughts: bool = True,
) -> BuiltInPlanner:
    """Create an ADK BuiltInPlanner safely aligned with the target model's thinking API."""
    spec = get_model_spec(model_id)
    desired = (thinking_level or "MEDIUM").upper()
    if desired not in spec.thinking_levels:
        desired = "HIGH" if "HIGH" in spec.thinking_levels else spec.thinking_levels[-1]

    if model_id.startswith("gemini-4") or model_id.startswith("gemini-3"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            thinking_cfg = types.ThinkingConfig(
                include_thoughts=include_thoughts,
                thinking_level=desired,  # type: ignore[arg-type]
            )
    else:
        budget_map = {"MINIMAL": 512, "LOW": 1024, "MEDIUM": 2048, "HIGH": 4096, "XHIGH": 8192}
        thinking_cfg = types.ThinkingConfig(
            include_thoughts=include_thoughts,
            thinking_budget=budget_map.get(desired, 2048),
        )
    return BuiltInPlanner(thinking_config=thinking_cfg)


def _make_specialist_agent(
    blueprint: AgentBlueprint,
    *,
    model_id: str,
    default_thinking_level: str,
    workspace: RunWorkspace,
    emit: EventCallback,
    extra_instruction: str = "",
    name_override: str | None = None,
    extra_tools: list[Any] | None = None,
) -> LlmAgent:
    tools = create_workspace_toolset(
        workspace,
        emit,
        include_code_runner=blueprint.include_code_runner,
        include_video_tools=blueprint.include_video_tools,
        include_finance_tools=blueprint.include_finance_tools,
    )
    if extra_tools:
        tools.extend(extra_tools)

    full_instruction = blueprint.instruction.strip()
    if extra_instruction:
        full_instruction = f"{full_instruction}\n\n{extra_instruction.strip()}"

    full_instruction += (
        "\n\nCollaboration Rules:\n"
        "- Always read the Team Blackboard when collaborating with peers so your output builds on theirs.\n"
        "- Save tangible deliverables into the workspace using `write_workspace_file` (never only paste large files into chat).\n"
        "- Keep responses concise, structured, and concrete."
    )

    level = blueprint.thinking_level or default_thinking_level
    return LlmAgent(
        name=name_override or blueprint.name,
        model=model_id,
        description=f"{blueprint.role}: {blueprint.specialty}",
        instruction=full_instruction,
        tools=tools,
        planner=build_thinking_planner(model_id, level, include_thoughts=True),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.45,
        ),
    )


def build_team_topology(
    *,
    scenario: ScenarioSpec,
    mode: CollaborationMode,
    worker_model: str,
    orchestrator_model: str,
    worker_thinking_level: str,
    orchestrator_thinking_level: str,
    workspace: RunWorkspace,
    emit: EventCallback,
    telemetry: RunTelemetry,
    custom_agents: list[AgentBlueprint] | None = None,
) -> tuple[BaseAgent, list[dict[str, Any]]]:
    """Assemble the requested Google ADK multi-agent topology and return `(root_agent, roster_meta)`."""
    blueprints = custom_agents if custom_agents else scenario.agents
    roster: list[dict[str, Any]] = []

    if mode == "orchestrated":
        orchestrator_name = "TeamOrchestrator"
        orch_spec = get_model_spec(orchestrator_model)
        telemetry.ensure_agent(
            orchestrator_name,
            role=f"Rank-Up Orchestrator ({orch_spec.display_name})",
            model=orchestrator_model,
            is_orchestrator=True,
        )
        roster.append(
            {
                "name": orchestrator_name,
                "role": f"Team Orchestrator ({orch_spec.symbol})",
                "specialty": "Decomposes goals, delegates to Hydrogen specialists, reviews blackboard, synthesizes final output",
                "model": orchestrator_model,
                "symbol": orch_spec.symbol,
                "accent_color": orch_spec.accent_color,
                "is_orchestrator": True,
                "thinking_level": orchestrator_thinking_level,
            }
        )

        agent_tools: list[Any] = []
        specialist_summaries: list[str] = []
        for bp in blueprints:
            w_spec = get_model_spec(worker_model)
            telemetry.ensure_agent(
                bp.name,
                role=bp.role,
                model=worker_model,
                is_orchestrator=False,
            )
            roster.append(
                {
                    "name": bp.name,
                    "role": bp.role,
                    "specialty": bp.specialty,
                    "model": worker_model,
                    "symbol": w_spec.symbol,
                    "accent_color": w_spec.accent_color,
                    "is_orchestrator": False,
                    "thinking_level": bp.thinking_level or worker_thinking_level,
                }
            )
            sub_agent = _make_specialist_agent(
                bp,
                model_id=worker_model,
                default_thinking_level=worker_thinking_level,
                workspace=workspace,
                emit=emit,
                extra_instruction=(
                    "You are being delegated a focused assignment by TeamOrchestrator. "
                    "Read the Team Blackboard first, execute your part completely (writing workspace files "
                    "and running code/renders as needed), post your key outputs to the Team Blackboard, "
                    "and return a concise status report."
                ),
            )
            agent_tools.append(AgentTool(agent=sub_agent))
            specialist_summaries.append(f"- `{bp.name}` ({bp.role}): {bp.specialty}")

        shared_tools = create_workspace_toolset(
            workspace,
            emit,
            include_code_runner=False,
            include_video_tools=False,
            include_finance_tools=False,
        )
        roster_text = "\n".join(specialist_summaries)
        orchestrator = LlmAgent(
            name=orchestrator_name,
            model=orchestrator_model,
            description=f"Higher-rank team orchestrator coordinating Hydrogen specialists for {scenario.name}.",
            instruction=(
                f"You are TeamOrchestrator leading a Hydrogen Team squad for: **{scenario.name}**.\n"
                f"Your specialist Hydrogen agents are available as tools:\n{roster_text}\n\n"
                "Execution Protocol:\n"
                "1. First post a brief kickoff plan to the Team Blackboard (`post_to_blackboard`, `kind='proposal'`).\n"
                "2. Delegate substantive work to your Hydrogen specialists by invoking their tools in logical order "
                "(ensure every relevant specialist contributes and builds on teammates' workspace files & blackboard notes).\n"
                "3. After specialists complete their deliverables, inspect `list_workspace_files` and `read_blackboard`.\n"
                "4. Post a final `decision` to the Team Blackboard and present a crisp, executive final summary "
                "highlighting how each Hydrogen specialist contributed and listing every saved deliverable file."
            ),
            tools=[*shared_tools, *agent_tools],
            planner=build_thinking_planner(
                orchestrator_model, orchestrator_thinking_level, include_thoughts=True
            ),
            generate_content_config=types.GenerateContentConfig(temperature=0.35),
        )
        return orchestrator, roster

    if mode == "peer_mesh":
        # Pure Hydrogen-to-Hydrogen collaboration — NO orchestrator!
        w_spec = get_model_spec(worker_model)
        for bp in blueprints:
            telemetry.ensure_agent(
                bp.name,
                role=bp.role,
                model=worker_model,
                is_orchestrator=False,
            )
            roster.append(
                {
                    "name": bp.name,
                    "role": bp.role,
                    "specialty": bp.specialty,
                    "model": worker_model,
                    "symbol": w_spec.symbol,
                    "accent_color": w_spec.accent_color,
                    "is_orchestrator": False,
                    "thinking_level": bp.thinking_level or worker_thinking_level,
                }
            )

        if len(blueprints) <= 2:
            seq_agents = [
                _make_specialist_agent(
                    bp,
                    model_id=worker_model,
                    default_thinking_level=worker_thinking_level,
                    workspace=workspace,
                    emit=emit,
                    extra_instruction="You are collaborating directly as peers with no central orchestrator.",
                )
                for bp in blueprints
            ]
            root = SequentialAgent(
                name="HydrogenPeerCollective",
                description="Peer-to-peer Hydrogen collective collaborating without an orchestrator.",
                sub_agents=seq_agents,
            )
            return root, roster

        # Phase 1: Parallel Discovery — first N-1 peers (or first 2 peers for ordered build flows)
        # work concurrently and post proposals/artifacts to the shared Team Blackboard.
        # For video_vfx/coding where builder depends on storyboard/architecture, parallel phase runs
        # the independent creative/design + companion peers, then sequential integration executes!
        parallel_bps = blueprints[:2]
        integration_bps = blueprints[2:]

        phase1_agents = [
            _make_specialist_agent(
                bp,
                model_id=worker_model,
                default_thinking_level=worker_thinking_level,
                workspace=workspace,
                emit=emit,
                extra_instruction=(
                    "PHASE 1 (Peer Mesh — Parallel Discovery, No Orchestrator): "
                    "You are working concurrently alongside your peer Hydrogen agents. "
                    "Produce your core workspace deliverable right away and post clear notes to the Team Blackboard "
                    "(`post_to_blackboard`) so your teammates can integrate and build on your work in Phase 2."
                ),
            )
            for bp in parallel_bps
        ]

        phase2_agents = [
            _make_specialist_agent(
                bp,
                model_id=worker_model,
                default_thinking_level=worker_thinking_level,
                workspace=workspace,
                emit=emit,
                extra_instruction=(
                    "PHASE 2 (Peer Mesh — Cross-Pollination & Build, No Orchestrator): "
                    "First call `read_blackboard` and `list_workspace_files` to inspect what your peers created in Phase 1. "
                    "Explicitly reference your teammates by name, post constructive peer feedback or handoffs to the blackboard, "
                    "and complete your build/render/verification deliverables in the workspace."
                ),
            )
            for bp in integration_bps
        ]

        # Final peer wrap-up re-engages the last specialist to produce the unified collective summary
        # if needed — note integration_bps[-1] already acts as peer finisher & publisher!
        parallel_phase = ParallelAgent(
            name="ParallelDiscoveryPhase",
            description="Hydrogen peers execute concurrently and publish proposals to the shared blackboard.",
            sub_agents=phase1_agents,
        )
        integration_phase = SequentialAgent(
            name="PeerIntegrationPhase",
            description="Hydrogen peers review teammates' blackboard posts, build integrated outputs, and finalize deliverables.",
            sub_agents=phase2_agents,
        )
        root = SequentialAgent(
            name="HydrogenPeerMesh",
            description="Decentralized Hydrogen-to-Hydrogen peer mesh with zero central orchestrator.",
            sub_agents=[parallel_phase, integration_phase],
        )
        return root, roster

    # Mode 3: pipeline_loop — Sequential Assembly Pipeline + Quality Critic Loop (ADK LoopAgent)
    w_spec = get_model_spec(worker_model)
    critic_model = orchestrator_model if orchestrator_model != worker_model else worker_model
    c_spec = get_model_spec(critic_model)

    pipeline_agents: list[BaseAgent] = []
    for idx, bp in enumerate(blueprints):
        is_critic = idx == len(blueprints) - 2 and len(blueprints) >= 3
        chosen_model = critic_model if is_critic else worker_model
        chosen_spec = c_spec if is_critic else w_spec
        telemetry.ensure_agent(
            bp.name,
            role=bp.role,
            model=chosen_model,
            is_orchestrator=False,
        )
        roster.append(
            {
                "name": bp.name,
                "role": bp.role,
                "specialty": bp.specialty,
                "model": chosen_model,
                "symbol": chosen_spec.symbol,
                "accent_color": chosen_spec.accent_color,
                "is_orchestrator": False,
                "thinking_level": bp.thinking_level or worker_thinking_level,
            }
        )

    if len(blueprints) >= 3:
        front_agents = [
            _make_specialist_agent(
                bp,
                model_id=worker_model,
                default_thinking_level=worker_thinking_level,
                workspace=workspace,
                emit=emit,
                extra_instruction="PIPELINE STAGE: Read the blackboard and build your stage artifacts cleanly for the next teammate.",
            )
            for bp in blueprints[:-2]
        ]
        critic_bp = blueprints[-2]
        finisher_bp = blueprints[-1]

        critic_agent = _make_specialist_agent(
            critic_bp,
            model_id=critic_model,
            default_thinking_level=orchestrator_thinking_level if critic_model != worker_model else worker_thinking_level,
            workspace=workspace,
            emit=emit,
            extra_tools=[exit_loop],
            extra_instruction=(
                "QUALITY GATE LOOP: Inspect all workspace deliverables (`list_workspace_files`) and `read_blackboard`. "
                "Post your thorough peer critique to the blackboard (`kind='critique'`). "
                "If all key artifacts are already complete and verified on a subsequent pass, call `exit_loop` to approve "
                "and finish the refinement loop; otherwise pass clear revision requests to the finisher."
            ),
        )
        finisher_agent = _make_specialist_agent(
            finisher_bp,
            model_id=worker_model,
            default_thinking_level=worker_thinking_level,
            workspace=workspace,
            emit=emit,
            extra_tools=[exit_loop],
            extra_instruction=(
                "REFINEMENT & FINALIZATION STAGE: Read the critic's blackboard feedback, address every point in the "
                "final workspace deliverables, post a `decision` to the blackboard, and call `exit_loop` once all "
                "deliverables are complete and polished."
            ),
        )
        quality_loop = LoopAgent(
            name="QualityRefinementLoop",
            description="Iterative critic-and-refiner loop ensuring polished deliverables.",
            sub_agents=[critic_agent, finisher_agent],
            max_iterations=2,
        )
        pipeline_agents = [*front_agents, quality_loop]
    else:
        pipeline_agents = [
            _make_specialist_agent(
                bp,
                model_id=worker_model,
                default_thinking_level=worker_thinking_level,
                workspace=workspace,
                emit=emit,
            )
            for bp in blueprints
        ]

    root = SequentialAgent(
        name="HydrogenPipelineLoop",
        description="Sequential Hydrogen assembly pipeline followed by an ADK LoopAgent quality gate.",
        sub_agents=pipeline_agents,
    )
    return root, roster
