"""FastAPI server endpoint & security tests (offline, no external Vertex AI calls)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hydrogen_team.config import Settings
from hydrogen_team.engine import RunManager
from hydrogen_team.server import create_app


def test_api_health_models_scenarios_and_runs(tmp_path: Path):
    cfg = Settings(HYDROGEN_RUNS_DIR=tmp_path)
    manager = RunManager(cfg)
    app = create_app(settings=cfg, run_manager=manager)
    client = TestClient(app)

    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"

    m = client.get("/api/models")
    assert m.status_code == 200
    model_ids = [item["id"] for item in m.json()["models"]]
    assert "gemini-4-hydrogen" in model_ids
    assert "gemini-4-neon" in model_ids

    s = client.get("/api/scenarios")
    assert s.status_code == 200
    sc_ids = [item["id"] for item in s.json()["scenarios"]]
    assert "video_vfx" in sc_ids
    assert "trip_planning" in sc_ids

    r = client.get("/api/runs")
    assert r.status_code == 200
    assert r.json()["runs"] == []

    missing = client.get("/api/runs/does-not-exist")
    assert missing.status_code == 404
