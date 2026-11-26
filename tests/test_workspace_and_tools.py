"""Unit tests for sandboxed RunWorkspace, Blackboard, Python runner, financial model, and FFmpeg video render."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from hydrogen_team.events import TeamEvent
from hydrogen_team.tools import create_workspace_toolset
from hydrogen_team.workspace import RunWorkspace


def test_workspace_blocks_path_traversal(tmp_path: Path):
    ws = RunWorkspace("test-run", tmp_path)
    with pytest.raises(ValueError):
        ws.resolve_safe_path("../../etc/passwd")
    with pytest.raises(ValueError):
        ws.write_text_file("../escape.txt", "nope")


def test_blackboard_and_artifacts_and_zip(tmp_path: Path):
    ws = RunWorkspace("test-run", tmp_path)
    entry = ws.post_blackboard(
        author="CreativeDirector",
        to_agent="MotionCoder",
        topic="Palette",
        kind="proposal",
        message="Use #38BDF8 hydrogen cyan.",
    )
    assert entry.seq == 1
    assert len(ws.read_blackboard()) == 1

    info = ws.write_text_file("studio.html", "<h1>Hello Hydrogen</h1>", author="MotionCoder")
    assert info.preview_kind == "html"
    assert ws.read_text_file("studio.html") == "<h1>Hello Hydrogen</h1>"

    bundle = ws.build_zip_bundle()
    assert bundle.is_file()
    assert bundle.stat().st_size > 100


def test_tools_python_runner_and_finance_and_ffmpeg(tmp_path: Path):
    ws = RunWorkspace("tool-run", tmp_path)
    captured: list[TeamEvent] = []
    tools = create_workspace_toolset(
        ws,
        captured.append,
        include_code_runner=True,
        include_video_tools=True,
        include_finance_tools=True,
    )
    tool_map = {fn.__name__: fn for fn in tools}

    # Test blackboard tool
    post_res = tool_map["post_to_blackboard"](
        topic="Kickoff", message="Ready to collaborate!", to_agent="all", kind="proposal"
    )
    assert post_res["status"] == "posted"
    assert any(e.kind == "blackboard_post" for e in captured)

    # Test deterministic financial model tool
    fin = tool_map["compute_financial_model"](
        monthly_price_usd=99.0,
        initial_customers=100,
        monthly_growth_rate=0.15,
        monthly_churn_rate=0.03,
        cac_usd=400.0,
        gross_margin=0.82,
        months=12,
    )
    assert fin["summary"]["ltv_to_cac_ratio"] > 6.0
    assert len(fin["timeline"]) == 12

    # Test sandboxed Python execution
    tool_map["write_workspace_file"](
        relative_path="gen_out.py",
        content="from pathlib import Path\nPath('result.csv').write_text('a,b\\n1,2\\n')\nprint('SCRIPT_OK')\n",
    )
    run_res = tool_map["run_python_script"](script_path="gen_out.py")
    assert run_res["status"] == "ok"
    assert "SCRIPT_OK" in run_res["stdout"]
    assert "result.csv" in run_res["generated_files"]

    # Test real FFmpeg procedural PNG frames -> MP4 video rendering when FFmpeg is installed
    if shutil.which("ffmpeg"):
        frames_dir = ws.workspace_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(1, 13):
            img = Image.new("RGB", (320, 180), (7, 11, 20))
            draw = ImageDraw.Draw(img)
            draw.ellipse((20 + idx * 12, 50, 100 + idx * 12, 130), outline=(56, 189, 248), width=4)
            img.save(frames_dir / f"frame_{idx:04d}.png")

        vid_res = tool_map["render_video_from_frames"](
            frames_pattern="frames/frame_%04d.png",
            output_filename="smoke.mp4",
            fps=12,
            add_ambient_audio=True,
        )
        assert vid_res["status"] == "rendered"
        assert vid_res["artifact"]["preview_kind"] == "video"
        assert (ws.workspace_dir / "smoke.mp4").stat().st_size > 1000
