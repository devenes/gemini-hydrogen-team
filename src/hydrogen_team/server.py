"""FastAPI backend for Hydrogen Team Mission Control: REST API, SSE telemetry stream, and artifact preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from hydrogen_team import __version__
from hydrogen_team.config import Settings, get_settings, inspect_environment
from hydrogen_team.engine import RunManager, RunRequest
from hydrogen_team.models import list_models, probe_all_models
from hydrogen_team.scenarios import list_scenarios


def _resolve_static_dir() -> Path | None:
    pkg_static = Path(__file__).resolve().parent / "static"
    if (pkg_static / "index.html").is_file():
        return pkg_static
    repo_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if (repo_dist / "index.html").is_file():
        return repo_dist
    return None


def create_app(
    settings: Settings | None = None,
    run_manager: RunManager | None = None,
) -> FastAPI:
    cfg = settings or get_settings()
    manager = run_manager or RunManager(cfg)

    app = FastAPI(
        title="Hydrogen Team — Multi-Agent Collaboration Studio",
        version=__version__,
        description=(
            "Open-source multi-agent collaboration engine powered by Google Gemini 4 Hydrogen "
            "and Google ADK."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = cfg
    app.state.run_manager = manager

    @app.get("/api/health")
    async def get_health() -> dict[str, Any]:
        env_status = inspect_environment(cfg)
        return {
            "status": "ok",
            "version": __version__,
            "environment": env_status.model_dump(),
        }

    @app.get("/api/models")
    async def get_models() -> dict[str, Any]:
        return {
            "models": [m.model_dump() for m in list_models()],
            "defaults": {
                "worker_model": cfg.default_worker_model,
                "orchestrator_model": cfg.default_orchestrator_model,
                "fallback_model": cfg.fallback_model,
                "thinking_level": cfg.default_thinking_level,
            },
        }

    @app.post("/api/models/probe")
    async def probe_models(force: bool = Query(default=False)) -> dict[str, Any]:
        results = await probe_all_models(cfg, force_refresh=force)
        return {
            "environment": inspect_environment(cfg).model_dump(),
            "results": [r.model_dump() for r in results],
        }

    @app.get("/api/scenarios")
    async def get_scenarios() -> dict[str, Any]:
        return {
            "scenarios": [s.model_dump() for s in list_scenarios()],
        }

    @app.get("/api/runs")
    async def get_runs() -> dict[str, Any]:
        return {
            "runs": [r.model_dump() for r in manager.list_runs()],
        }

    @app.post("/api/runs")
    async def start_run(request: RunRequest) -> dict[str, Any]:
        try:
            active = await manager.start_run(request)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return active.summary.model_dump()

    @app.get("/api/runs/{run_id}")
    async def get_run_detail(run_id: str) -> dict[str, Any]:
        run = manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        return {
            "summary": run.summary.model_dump(),
            "events": [e.model_dump() for e in run.events],
            "blackboard": [b.model_dump() for b in run.workspace.read_blackboard(limit=100)],
            "artifacts": [a.model_dump() for a in run.workspace.list_artifacts()],
        }

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str) -> dict[str, Any]:
        cancelled = await manager.cancel_run(run_id)
        if not cancelled:
            raise HTTPException(status_code=400, detail="Run is not active or does not exist.")
        return {"status": "cancelled", "run_id": run_id}

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str) -> EventSourceResponse:
        run = manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

        async def event_generator():
            async for event in run.subscribe():
                yield {
                    "event": event.kind,
                    "id": str(event.seq),
                    "data": json.dumps(event.model_dump(), ensure_ascii=False),
                }
            yield {
                "event": "stream_end",
                "data": json.dumps({"run_id": run_id, "status": run.summary.status}),
            }

        return EventSourceResponse(event_generator())

    @app.get("/api/runs/{run_id}/artifacts")
    async def list_run_artifacts(run_id: str) -> dict[str, Any]:
        run = manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        return {"artifacts": [a.model_dump() for a in run.workspace.list_artifacts()]}

    @app.get("/api/runs/{run_id}/artifacts/{file_path:path}")
    async def get_artifact(run_id: str, file_path: str) -> FileResponse:
        run = manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        try:
            resolved = run.workspace.resolve_safe_path(file_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail=f"Artifact '{file_path}' not found.")
        return FileResponse(path=resolved)

    @app.get("/api/runs/{run_id}/download")
    async def download_bundle(run_id: str) -> FileResponse:
        run = manager.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        zip_path = run.workspace.build_zip_bundle()
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=zip_path.name,
        )

    static_dir = _resolve_static_dir()
    if static_dir:
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_spa_root() -> FileResponse:
            return FileResponse(static_dir / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found.")
            candidate = (static_dir / full_path).resolve()
            try:
                candidate.relative_to(static_dir.resolve())
                if candidate.is_file():
                    return FileResponse(candidate)
            except ValueError:
                pass
            return FileResponse(static_dir / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        async def serve_dev_notice() -> HTMLResponse:
            return HTMLResponse(
                "<h1>Hydrogen Team API is running</h1>"
                "<p>Build the frontend with <code>cd web && npm install && npm run build</code> "
                "or run the Vite dev server on port 5173.</p>"
            )

    return app


app = create_app()
