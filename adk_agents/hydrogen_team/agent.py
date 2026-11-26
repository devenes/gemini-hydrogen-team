"""Native Google ADK entry point exposing `root_agent` for `adk web` and `adk run`.

Usage:
    adk web adk_agents
    adk run adk_agents/hydrogen_team

Configure via environment variables:
    HYDROGEN_ADK_SCENARIO=video_vfx|coding|company_ops|research|trip_planning|product_launch
    HYDROGEN_ADK_MODE=peer_mesh|orchestrated|pipeline_loop
    HYDROGEN_WORKER_MODEL=gemini-4-hydrogen
    HYDROGEN_ORCHESTRATOR_MODEL=gemini-4-neon
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local `src/` is importable even if `adk web` runs without editable install.
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydrogen_team.config import get_settings  # noqa: E402
from hydrogen_team.events import RunTelemetry  # noqa: E402
from hydrogen_team.scenarios import CollaborationMode, get_scenario  # noqa: E402
from hydrogen_team.topologies import build_team_topology  # noqa: E402
from hydrogen_team.workspace import RunWorkspace  # noqa: E402

_settings = get_settings()
_settings.apply_runtime_env()

_scenario_id = os.getenv("HYDROGEN_ADK_SCENARIO", "video_vfx")
_mode_raw = os.getenv("HYDROGEN_ADK_MODE", "peer_mesh")
_mode: CollaborationMode = (
    _mode_raw if _mode_raw in {"orchestrated", "peer_mesh", "pipeline_loop"} else "peer_mesh"  # type: ignore[assignment]
)

_scenario = get_scenario(_scenario_id)
_workspace = RunWorkspace(f"adk-web-{_scenario.id}", _settings.runs_dir)
_telemetry = RunTelemetry(run_id=_workspace.run_id)

root_agent, _roster = build_team_topology(
    scenario=_scenario,
    mode=_mode,
    worker_model=_settings.default_worker_model,
    orchestrator_model=_settings.default_orchestrator_model,
    worker_thinking_level=_settings.default_thinking_level,
    orchestrator_thinking_level="HIGH",
    workspace=_workspace,
    emit=lambda _evt: None,
    telemetry=_telemetry,
)
