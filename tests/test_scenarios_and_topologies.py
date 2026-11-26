"""Unit tests for all scenarios, ADK topologies, and native `adk_agents` compatibility."""

from __future__ import annotations

from pathlib import Path

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent

from hydrogen_team.events import RunTelemetry
from hydrogen_team.scenarios import get_scenario, list_scenarios
from hydrogen_team.topologies import build_team_topology
from hydrogen_team.workspace import RunWorkspace


def test_all_scenarios_have_agents_and_three_templates():
    scenarios = list_scenarios()
    ids = {s.id for s in scenarios}
    assert {"video_vfx", "coding", "company_ops", "research", "trip_planning", "product_launch"} <= ids
    for sc in scenarios:
        assert len(sc.agents) >= 3
        assert len(sc.templates) >= 3


def test_build_all_three_adk_topologies(tmp_path: Path):
    scenario = get_scenario("video_vfx")

    for mode in ("peer_mesh", "orchestrated", "pipeline_loop"):
        ws = RunWorkspace(f"topo-{mode}", tmp_path)
        tel = RunTelemetry(run_id=ws.run_id)
        root, roster = build_team_topology(
            scenario=scenario,
            mode=mode,  # type: ignore[arg-type]
            worker_model="gemini-4-hydrogen",
            orchestrator_model="gemini-4-neon",
            worker_thinking_level="MEDIUM",
            orchestrator_thinking_level="HIGH",
            workspace=ws,
            emit=lambda _e: None,
            telemetry=tel,
        )
        assert isinstance(root, BaseAgent)
        if mode == "orchestrated":
            assert isinstance(root, LlmAgent)
            assert any(m["is_orchestrator"] for m in roster)
            assert len(roster) == len(scenario.agents) + 1
        else:
            assert isinstance(root, SequentialAgent)
            assert not any(m["is_orchestrator"] for m in roster)
            assert len(roster) == len(scenario.agents)


def test_native_adk_agents_package_exposes_root_agent():
    import importlib.util

    agent_file = Path(__file__).resolve().parents[1] / "adk_agents" / "hydrogen_team" / "agent.py"
    spec = importlib.util.spec_from_file_location("adk_hydrogen_team_agent", agent_file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "root_agent")
    assert isinstance(mod.root_agent, BaseAgent)
