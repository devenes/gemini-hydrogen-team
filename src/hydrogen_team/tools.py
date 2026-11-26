"""Sandboxed ADK tools enabling Hydrogen agents to collaborate, write code, model finances, and render videos."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from google.adk.tools import ToolContext

from hydrogen_team.events import TeamEvent
from hydrogen_team.workspace import BlackboardKind, RunWorkspace

EventCallback = Callable[[TeamEvent], None]

_VALID_BLACKBOARD_KINDS = {"proposal", "finding", "critique", "decision", "handoff", "question"}


def create_workspace_toolset(
    workspace: RunWorkspace,
    emit: EventCallback,
    *,
    include_code_runner: bool = True,
    include_video_tools: bool = False,
    include_finance_tools: bool = False,
) -> list[Callable[..., Any]]:
    """Build ADK-compatible tool functions scoped strictly to a single RunWorkspace."""

    def _agent_name(tool_context: ToolContext | None) -> str:
        if tool_context is not None:
            name = getattr(tool_context, "agent_name", None)
            if name:
                return str(name)
        return "agent"

    def post_to_blackboard(
        topic: str,
        message: str,
        to_agent: str = "all",
        kind: str = "finding",
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Post a structured collaboration message to the shared Team Blackboard.

        Use this to share findings, proposals, peer critiques, questions, or handoffs
        with teammates so every agent can coordinate transparently.

        Args:
            topic: Short subject heading (e.g. 'Architecture Proposal', 'VFX Render Plan').
            message: Clear, concise collaboration note with actionable details.
            to_agent: Target teammate name (e.g. 'MotionCoder') or 'all' for the whole squad.
            kind: One of 'proposal', 'finding', 'critique', 'decision', 'handoff', 'question'.
        """
        author = _agent_name(tool_context)
        normalized_kind: BlackboardKind = (
            kind if kind in _VALID_BLACKBOARD_KINDS else "finding"  # type: ignore[assignment]
        )
        entry = workspace.post_blackboard(
            author=author,
            topic=topic,
            message=message,
            to_agent=to_agent or "all",
            kind=normalized_kind,
        )
        emit(
            TeamEvent(
                run_id=workspace.run_id,
                kind="blackboard_post",
                agent=author,
                target_agent=entry.to_agent,
                title=f"[{entry.kind.upper()}] {entry.topic}",
                content=entry.message,
                data=entry.model_dump(),
            )
        )
        return {"status": "posted", "seq": entry.seq, "author": author, "to_agent": entry.to_agent}

    def read_blackboard(
        limit: int = 30,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Read recent peer collaboration messages from the shared Team Blackboard.

        Args:
            limit: Maximum number of recent entries to return (default 30).
        """
        entries = workspace.read_blackboard(limit=max(1, min(limit, 100)))
        return {
            "count": len(entries),
            "entries": [e.model_dump() for e in entries],
        }

    def write_workspace_file(
        relative_path: str,
        content: str,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Create or update a file inside the shared run workspace.

        Use this to deliver code, HTML5 interactive previews/animations, Markdown reports,
        Python scripts, CSS, JSON, or CSV artifacts.

        Args:
            relative_path: Relative file path inside the workspace (e.g. 'report.md', 'app/main.py', 'studio.html').
            content: Complete UTF-8 text content of the file.
        """
        author = _agent_name(tool_context)
        info = workspace.write_text_file(relative_path, content, author=author)
        emit(
            TeamEvent(
                run_id=workspace.run_id,
                kind="artifact_created",
                agent=author,
                title=f"Saved {info.path}",
                content=f"Wrote {info.size_bytes:,} bytes ({info.preview_kind})",
                data=info.model_dump(),
            )
        )
        return {"status": "saved", "artifact": info.model_dump()}

    def read_workspace_file(
        relative_path: str,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Read a UTF-8 file from the shared run workspace created by you or a teammate.

        Args:
            relative_path: Relative path of the file inside the workspace.
        """
        try:
            text = workspace.read_text_file(relative_path)
            return {"status": "ok", "path": relative_path, "content": text}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def list_workspace_files(tool_context: ToolContext | None = None) -> dict[str, Any]:
        """List all files currently saved in the shared run workspace."""
        artifacts = workspace.list_artifacts()
        return {
            "count": len(artifacts),
            "files": [a.model_dump() for a in artifacts],
        }

    def run_python_script(
        script_path: str,
        timeout_seconds: int = 45,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Execute a Python script inside the sandboxed run workspace and inspect its output.

        Useful for running unit tests, executing financial simulations, or rendering procedural
        Pillow video frames without After Effects or Premiere.

        Args:
            script_path: Relative path to the Python script inside the workspace.
            timeout_seconds: Maximum runtime in seconds (clamped between 5 and 90).
        """
        author = _agent_name(tool_context)
        try:
            resolved = workspace.resolve_safe_path(script_path)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        if not resolved.is_file():
            return {"status": "error", "error": f"Script not found: {script_path}"}

        before_files = {a.path: a.updated_at for a in workspace.list_artifacts()}
        timeout = max(5, min(int(timeout_seconds), 90))
        try:
            proc = subprocess.run(
                [sys.executable, str(resolved)],
                cwd=str(workspace.workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": f"Script exceeded timeout of {timeout}s.",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

        # Register any newly created or updated artifacts (e.g. PNGs, MP4s, CSVs).
        new_artifacts: list[str] = []
        for art in workspace.list_artifacts():
            prev_mtime = before_files.get(art.path)
            if prev_mtime is None or art.updated_at > prev_mtime + 0.001:
                info = workspace.register_generated_file(art.path, author=author)
                new_artifacts.append(info.path)
                # Avoid spamming 180 frame PNG events; emit for key deliverables & first frame.
                if not info.path.startswith("frames/") or info.path.endswith("0001.png"):
                    emit(
                        TeamEvent(
                            run_id=workspace.run_id,
                            kind="artifact_created",
                            agent=author,
                            title=f"Generated {info.path}",
                            content=f"Produced by {script_path} ({info.size_bytes:,} bytes)",
                            data=info.model_dump(),
                        )
                    )

        return {
            "status": "ok" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-4000:],
            "generated_files": new_artifacts[:30],
        }

    def render_video_from_frames(
        frames_pattern: str = "frames/frame_%04d.png",
        output_filename: str = "final_video.mp4",
        fps: int = 30,
        add_ambient_audio: bool = True,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Assemble a numbered PNG image sequence in the workspace into a web-playable H.264 MP4 using FFmpeg.

        No After Effects or Premiere required — pair this with a Python/Pillow animation script.

        Args:
            frames_pattern: Relative printf pattern inside the workspace (e.g. 'frames/frame_%04d.png').
            output_filename: Relative output `.mp4` path (e.g. 'hydrogen_teaser.mp4').
            fps: Frames per second (default 30, clamped 10..60).
            add_ambient_audio: If True, synthesizes a subtle harmonic ambient audio bed via FFmpeg.
        """
        author = _agent_name(tool_context)
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return {
                "status": "error",
                "error": "FFmpeg is not installed on this machine. Deliver an interactive HTML5 Canvas animation instead.",
            }

        try:
            output_path = workspace.resolve_safe_path(output_filename)
            if not output_path.suffix.lower() == ".mp4":
                output_path = output_path.with_suffix(".mp4")
            # Validate frames directory stays within workspace.
            pattern_parent = workspace.resolve_safe_path(
                str(frames_pattern).replace("%04d", "0001").replace("%03d", "001").replace("%d", "1")
            ).parent
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}

        if not pattern_parent.exists():
            return {
                "status": "error",
                "error": f"Frames directory does not exist yet: {pattern_parent.name}",
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        clamped_fps = max(10, min(int(fps), 60))
        pattern_abs = str((workspace.workspace_dir / frames_pattern.lstrip("/")).resolve())

        cmd = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(clamped_fps),
            "-i",
            pattern_abs,
        ]
        if add_ambient_audio:
            cmd.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "aevalsrc=0.06*sin(2*PI*220*t)+0.04*sin(2*PI*330*t)+0.025*sin(2*PI*440*t):s=44100",
                    "-shortest",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                ]
            )
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                str(output_path),
            ]
        )

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(workspace.workspace_dir),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "FFmpeg render timed out after 60s."}

        if proc.returncode != 0 or not output_path.is_file():
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stderr": proc.stderr[-3000:],
            }

        rel = output_path.relative_to(workspace.workspace_dir).as_posix()
        info = workspace.register_generated_file(rel, author=author)
        emit(
            TeamEvent(
                run_id=workspace.run_id,
                kind="artifact_created",
                agent=author,
                title=f"Rendered video {info.path}",
                content=f"H.264 MP4 rendered at {clamped_fps}fps ({info.size_bytes:,} bytes)",
                data=info.model_dump(),
            )
        )
        return {"status": "rendered", "artifact": info.model_dump()}

    def compute_financial_model(
        monthly_price_usd: float,
        initial_customers: int,
        monthly_growth_rate: float,
        monthly_churn_rate: float,
        cac_usd: float,
        gross_margin: float = 0.82,
        months: int = 12,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Run an exact multi-month SaaS/business unit-economics and ARR projection model.

        Args:
            monthly_price_usd: Average monthly revenue per customer (ARPU) in USD.
            initial_customers: Starting active paying customer count at Month 1.
            monthly_growth_rate: Monthly gross new customer acquisition rate (e.g. 0.15 for 15%).
            monthly_churn_rate: Monthly customer churn rate (e.g. 0.03 for 3%).
            cac_usd: Customer acquisition cost in USD.
            gross_margin: Gross margin ratio between 0.0 and 1.0 (default 0.82).
            months: Number of months to project (between 3 and 36).
        """
        m_count = max(3, min(int(months), 36))
        customers = float(max(initial_customers, 1))
        margin = max(0.05, min(float(gross_margin), 0.99))
        churn = max(0.001, min(float(monthly_churn_rate), 0.95))
        growth = max(0.0, min(float(monthly_growth_rate), 2.0))

        ltv = (monthly_price_usd * margin) / churn
        ltv_cac = ltv / max(cac_usd, 1.0)
        payback_months = cac_usd / max(monthly_price_usd * margin, 0.01)

        timeline: list[dict[str, Any]] = []
        cum_rev = 0.0
        cum_gp = 0.0
        cum_cac_spend = 0.0

        for m in range(1, m_count + 1):
            new_cust = customers * growth
            churned = customers * churn
            if m > 1:
                customers = max(0.0, customers + new_cust - churned)
            mrr = customers * monthly_price_usd
            arr = mrr * 12.0
            gp = mrr * margin
            cac_spend = new_cust * cac_usd
            cum_rev += mrr
            cum_gp += gp
            cum_cac_spend += cac_spend
            timeline.append(
                {
                    "month": m,
                    "active_customers": round(customers),
                    "new_customers": round(new_cust),
                    "churned_customers": round(churned),
                    "mrr_usd": round(mrr, 2),
                    "arr_usd": round(arr, 2),
                    "gross_profit_usd": round(gp, 2),
                    "net_contribution_usd": round(gp - cac_spend, 2),
                }
            )

        summary = {
            "ltv_usd": round(ltv, 2),
            "cac_usd": round(cac_usd, 2),
            "ltv_to_cac_ratio": round(ltv_cac, 2),
            "cac_payback_months": round(payback_months, 2),
            "ending_customers": timeline[-1]["active_customers"],
            "ending_mrr_usd": timeline[-1]["mrr_usd"],
            "ending_arr_usd": timeline[-1]["arr_usd"],
            "cumulative_revenue_usd": round(cum_rev, 2),
            "cumulative_gross_profit_usd": round(cum_gp, 2),
            "cumulative_cac_spend_usd": round(cum_cac_spend, 2),
            "rule_of_thumb_health": (
                "Strong (LTV:CAC >= 3x)" if ltv_cac >= 3.0 else "Needs Retention/Pricing Optimization"
            ),
            "is_finite": math.isfinite(ltv),
        }
        return {"summary": summary, "timeline": timeline}

    tools: list[Callable[..., Any]] = [
        post_to_blackboard,
        read_blackboard,
        write_workspace_file,
        read_workspace_file,
        list_workspace_files,
    ]
    if include_code_runner:
        tools.append(run_python_script)
    if include_video_tools:
        tools.append(render_video_from_frames)
    if include_finance_tools:
        tools.append(compute_financial_model)
    return tools


def summarize_tool_result(result: Any, max_len: int = 500) -> str:
    """Produce a concise human-readable preview of a tool result for telemetry logs."""
    try:
        text = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
    except Exception:
        text = str(result)
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text
