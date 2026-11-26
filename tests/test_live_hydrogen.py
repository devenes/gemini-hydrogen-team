"""Live end-to-end Vertex AI Gemini 4 Hydrogen multi-agent collaboration tests.

Run with: pytest -m live -s
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hydrogen_team.config import Settings, inspect_environment
from hydrogen_team.engine import RunManager, RunRequest
from hydrogen_team.models import probe_all_models

pytestmark = pytest.mark.live


async def test_live_probe_gemini_4_periodic_table():
    settings = Settings()
    env = inspect_environment(settings)
    assert env.auth_mode != "unconfigured", "GCP Vertex AI ADC or GEMINI_API_KEY must be configured"

    results = await probe_all_models(settings, force_refresh=True)
    by_id = {r.model_id: r for r in results}
    assert by_id["gemini-4-hydrogen"].available, f"Hydrogen probe failed: {by_id['gemini-4-hydrogen'].error}"
    assert by_id["gemini-2.5-flash"].available


async def test_live_peer_mesh_video_vfx_hydrogen_collaboration(tmp_path: Path):
    """End-to-end pure Hydrogen peer-mesh test (NO orchestrator) rendering a real MP4 + HTML5 studio."""
    settings = Settings(HYDROGEN_RUNS_DIR=tmp_path)
    manager = RunManager(settings)
    req = RunRequest(
        scenario_id="video_vfx",
        mode="peer_mesh",
        worker_model="gemini-4-hydrogen",
        orchestrator_model="gemini-4-hydrogen",
        worker_thinking_level="LOW",
        orchestrator_thinking_level="LOW",
        prompt=(
            "Create a fast 2-second (48 frames @ 24fps, 640x360) kinetic typography + glowing cyan "
            "orbital teaser for 'HYDROGEN TEAM' completely with code (no After Effects). "
            "Deliver storyboard.md, motion_studio.html, render_frames.py, and render hydrogen_studio_render.mp4 via FFmpeg."
        ),
    )
    active = await manager.start_run(req)
    assert active.task is not None
    await active.task

    assert active.summary.status == "completed", f"Run failed: {active.summary.error}"
    assert active.summary.resolved_worker_model == "gemini-4-hydrogen"
    assert active.summary.telemetry.total_tokens > 0
    assert active.summary.telemetry.total_blackboard_posts >= 2
    assert any(e.kind == "thought" for e in active.events), "Expected native Gemini 4 thinking traces"

    artifact_paths = {a.path for a in active.workspace.list_artifacts()}
    assert "motion_studio.html" in artifact_paths
    assert "hydrogen_studio_render.mp4" in artifact_paths, f"Artifacts were: {artifact_paths}"
    assert (active.workspace.workspace_dir / "hydrogen_studio_render.mp4").stat().st_size > 2000


async def test_live_orchestrated_coding_squad_argon_and_hydrogen(tmp_path: Path):
    """End-to-end Orchestrated Rank-Up test: Gemini 4 Hydrogen orchestrator + Gemini 4 Hydrogen workers."""
    settings = Settings(
        HYDROGEN_RUNS_DIR=tmp_path,
        HYDROGEN_LLM_TIMEOUT_MS=45_000,
        HYDROGEN_RUN_TIMEOUT_SECONDS=180,
    )
    manager = RunManager(settings)
    req = RunRequest(
        scenario_id="coding",
        mode="orchestrated",
        worker_model="gemini-4-hydrogen",
        orchestrator_model="gemini-4-hydrogen",
        worker_thinking_level="LOW",
        orchestrator_thinking_level="LOW",
        prompt=(
            "Build a concise thread-safe TokenBucket rate limiter in `rate_limiter.py` with injectable clock "
            "and verify it by running a real unittest file `test_solution.py` via `run_python_script`. "
            "Keep files tight and fast."
        ),
    )
    active = await manager.start_run(req)
    assert active.task is not None
    await active.task

    assert active.summary.status == "completed", f"Run failed: {active.summary.error}"
    assert active.summary.resolved_orchestrator_model == "gemini-4-hydrogen"
    assert active.summary.resolved_worker_model == "gemini-4-hydrogen"
    assert any(e.kind == "handoff" for e in active.events), "Expected orchestrator -> Hydrogen handoff events"
    assert active.summary.telemetry.total_artifacts >= 2
