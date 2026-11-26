"""Hydrogen Team CLI — run multi-agent Hydrogen squads, probe GCP Vertex AI models, and launch Mission Control."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from hydrogen_team import __version__
from hydrogen_team.config import get_settings, inspect_environment
from hydrogen_team.engine import RunManager, RunRequest
from hydrogen_team.models import get_model_spec, list_models, probe_all_models
from hydrogen_team.scenarios import CollaborationMode, get_scenario, list_scenarios

app = typer.Typer(
    name="hydrogen-team",
    help="Multi-agent collaboration studio powered by Google Gemini 4 Hydrogen & Google ADK.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version() -> None:
    """Print Hydrogen Team version."""
    console.print(f"[bold cyan]Hydrogen Team[/bold cyan] v{__version__}")


@app.command()
def doctor(
    probe: Annotated[
        bool,
        typer.Option("--probe/--no-probe", help="Live-probe Vertex AI / Gemini models."),
    ] = True,
) -> None:
    """Inspect Google Cloud ADC authentication, FFmpeg, Google ADK, and Gemini 4 model availability."""
    settings = get_settings()
    env = inspect_environment(settings)

    env_table = Table(title="Hydrogen Team Environment", show_header=False, border_style="cyan")
    env_table.add_column("Key", style="bold")
    env_table.add_column("Value")
    env_table.add_row("Auth Mode", f"[green]{env.auth_mode}[/green]" if env.auth_mode != "unconfigured" else "[red]unconfigured[/red]")
    env_table.add_row("GCP Project", env.gcp_project or "[yellow](not set)[/yellow]")
    env_table.add_row("GCP Location", env.gcp_location)
    env_table.add_row("Active Account", env.gcp_account or "-")
    env_table.add_row("ADC Credentials", "[green]Ready[/green]" if env.adc_available else "[yellow]Missing[/yellow]")
    env_table.add_row("Gemini API Key", "Configured" if env.api_key_configured else "Not used (ADC default)")
    env_table.add_row("Google ADK", env.adk_version)
    env_table.add_row("FFmpeg (Video Render)", "[green]Installed[/green]" if env.ffmpeg_available else "[yellow]Not installed[/yellow]")
    console.print(env_table)

    if not probe:
        return

    console.print("\n[cyan]Probing Gemini 4 Periodic Table & Fallback models...[/cyan]")
    results = asyncio.run(probe_all_models(settings, force_refresh=True))
    m_table = Table(title="Model Availability Matrix", border_style="bright_blue")
    m_table.add_column("El", justify="center", style="bold")
    m_table.add_column("Model ID", style="cyan")
    m_table.add_column("Rank")
    m_table.add_column("Status")
    m_table.add_column("Latency", justify="right")
    m_table.add_column("Notes")

    for res in results:
        spec = get_model_spec(res.model_id)
        status_str = "[bold green]AVAILABLE[/bold green]" if res.available else "[bold red]UNAVAILABLE[/bold red]"
        lat = f"{res.latency_ms} ms" if res.latency_ms is not None else "-"
        m_table.add_row(
            spec.symbol,
            res.model_id,
            spec.rank,
            status_str,
            lat,
            res.error or spec.tagline,
        )
    console.print(m_table)


@app.command()
def scenarios() -> None:
    """List all built-in multi-agent scenarios and starter prompt templates."""
    for sc in list_scenarios():
        table = Table(
            title=f"[bold cyan]{sc.id}[/bold cyan] — {sc.name} ({sc.category})",
            border_style="blue",
            expand=True,
        )
        table.add_column("#", width=3, justify="center")
        table.add_column("Template", style="bold")
        table.add_column("Badge", style="magenta")
        table.add_column("Expected Deliverables")
        for idx, tmpl in enumerate(sc.templates):
            table.add_row(
                str(idx),
                tmpl.title,
                tmpl.badge,
                ", ".join(tmpl.expected_deliverables),
            )
        agents_line = " • ".join(f"[cyan]{a.name}[/cyan] ({a.role})" for a in sc.agents)
        console.print(table)
        console.print(f"  [dim]Squad:[/dim] {agents_line}")
        console.print(
            f"  [dim]Default mode:[/dim] [green]{sc.recommended_mode}[/green]  "
            f"[dim]Recommended rank-up lead:[/dim] [yellow]{sc.recommended_orchestrator}[/yellow]\n"
        )


@app.command()
def models() -> None:
    """Display the Gemini 4 Periodic Table model lineup and pricing."""
    table = Table(title="Gemini 4 Periodic Table — Hydrogen Team Catalog", border_style="cyan")
    table.add_column("Symbol", justify="center", style="bold")
    table.add_column("Model ID", style="cyan")
    table.add_column("Role")
    table.add_column("Input / 1M", justify="right")
    table.add_column("Output / 1M", justify="right")
    table.add_column("Thinking Levels")
    for m in list_models():
        table.add_row(
            f"{m.atomic_number} {m.symbol}",
            m.id,
            m.tagline,
            f"${m.input_price_per_1m:.2f}",
            f"${m.output_price_per_1m:.2f}",
            ", ".join(m.thinking_levels),
        )
    console.print(table)


@app.command()
def run(
    scenario: Annotated[str, typer.Option("--scenario", "-s", help="Scenario ID (e.g. video_vfx, coding, company_ops, research, trip_planning, product_launch)")] = "video_vfx",
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Custom mission prompt")] = None,
    template: Annotated[int, typer.Option("--template", "-t", help="Template index if --prompt is omitted")] = 0,
    mode: Annotated[str, typer.Option("--mode", "-m", help="Collaboration mode: peer_mesh | orchestrated | pipeline_loop")] = "peer_mesh",
    worker_model: Annotated[str, typer.Option("--worker-model", help="Model for specialist agents")] = "gemini-4-hydrogen",
    orchestrator_model: Annotated[str, typer.Option("--orchestrator-model", help="Model for rank-up orchestrator / critic")] = "gemini-4-argon",
    thinking: Annotated[str, typer.Option("--thinking", help="Thinking level: LOW | MEDIUM | HIGH | XHIGH")] = "MEDIUM",
    show_thoughts: Annotated[bool, typer.Option("--thoughts/--no-thoughts", help="Display internal Gemini 4 thinking traces")] = True,
    auto_fallback: Annotated[bool, typer.Option("--auto-fallback/--no-auto-fallback", help="Fall back to Gemini 2.5 Flash if Hydrogen is unavailable")] = True,
) -> None:
    """Run a collaborative Hydrogen Team mission directly from the terminal with live telemetry."""
    sc = get_scenario(scenario)
    if prompt is None:
        if template < 0 or template >= len(sc.templates):
            raise typer.BadParameter(f"Template index must be between 0 and {len(sc.templates) - 1}.")
        chosen_prompt = sc.templates[template].prompt
    else:
        chosen_prompt = prompt

    if mode not in {"peer_mesh", "orchestrated", "pipeline_loop"}:
        raise typer.BadParameter("Mode must be one of: peer_mesh, orchestrated, pipeline_loop")

    typed_mode: CollaborationMode = mode  # type: ignore[assignment]

    async def _run_cli() -> None:
        settings = get_settings()
        manager = RunManager(settings)
        req = RunRequest(
            scenario_id=scenario,
            prompt=chosen_prompt,
            mode=typed_mode,
            worker_model=worker_model,
            orchestrator_model=orchestrator_model,
            worker_thinking_level=thinking.upper(),
            orchestrator_thinking_level="HIGH",
            auto_fallback=auto_fallback,
        )
        active = await manager.start_run(req)
        console.print(
            Panel(
                f"[bold]Run ID:[/bold] {active.summary.run_id}\n"
                f"[bold]Scenario:[/bold] {sc.name}\n"
                f"[bold]Mode:[/bold] {typed_mode}\n"
                f"[bold]Workers:[/bold] {worker_model}  •  [bold]Lead:[/bold] {orchestrator_model}\n"
                f"[bold]Workspace:[/bold] {active.workspace.workspace_dir}",
                title="Hydrogen Team Mission Launched",
                border_style="cyan",
            )
        )

        async for evt in active.subscribe():
            if evt.kind == "fallback_notice":
                console.print(Panel(evt.content, title="Model Fallback Notice", border_style="yellow"))
            elif evt.kind == "phase_changed":
                console.rule(f"[bold magenta]{evt.title}[/bold magenta]")
            elif evt.kind == "agent_started":
                console.print(f"[bold cyan]▶ {evt.agent}[/bold cyan] [dim]({evt.model})[/dim] started")
            elif evt.kind == "thought" and show_thoughts:
                preview = evt.content if len(evt.content) <= 500 else evt.content[:500] + "…"
                console.print(Panel(Text(preview, style="dim italic"), title=f"Thought • {evt.agent}", border_style="bright_black"))
            elif evt.kind == "handoff":
                console.print(f"  [bold yellow]⚡ Handoff[/bold yellow] [cyan]{evt.agent}[/cyan] → [green]{evt.target_agent}[/green]: {evt.content[:180]}")
            elif evt.kind == "blackboard_post":
                console.print(f"  [bold magenta]📌 Blackboard[/bold magenta] [cyan]{evt.agent}[/cyan] → [white]{evt.target_agent}[/white] {evt.title}: {evt.content[:220]}")
            elif evt.kind == "tool_call":
                console.print(f"  [blue]⚙ {evt.agent}[/blue] {evt.title} [dim]{evt.content[:140]}[/dim]")
            elif evt.kind == "artifact_created":
                console.print(f"  [bold green]✦ Artifact[/bold green] ({evt.agent}) {evt.title} — [dim]{evt.content}[/dim]")
            elif evt.kind == "message":
                console.print(Panel(evt.content[:1200], title=f"{evt.agent} ({evt.model})", border_style="cyan"))
            elif evt.kind == "error":
                console.print(Panel(evt.content, title=f"Error • {evt.agent}", border_style="red"))
            elif evt.kind == "run_completed":
                t = active.summary.telemetry
                summary_text = (
                    f"[bold green]Status:[/bold green] Completed\n"
                    f"[bold]Tokens:[/bold] {t.total_tokens:,} (in: {t.total_prompt_tokens:,} | out: {t.total_output_tokens:,} | thoughts: {t.total_thoughts_tokens:,})\n"
                    f"[bold]Estimated Cost:[/bold] ${t.total_cost_usd:.5f}  "
                    f"[green](Saved ${t.estimated_savings_vs_neon_usd:.5f} vs all-Neon)[/green]\n"
                    f"[bold]Artifacts Saved:[/bold] {t.total_artifacts} in {active.workspace.workspace_dir}"
                )
                console.print(Panel(summary_text, title="Mission Telemetry", border_style="green"))

    asyncio.run(_run_cli())


@app.command()
def web(
    host: Annotated[str, typer.Option("--host", "-h", help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Bind port")] = 8042,
    reload: Annotated[bool, typer.Option("--reload", help="Auto-reload backend on edits")] = False,
) -> None:
    """Launch the Hydrogen Team Mission Control Web UI & FastAPI SSE server."""
    console.print(
        Panel(
            f"[bold cyan]Hydrogen Team Mission Control[/bold cyan]\n"
            f"URL: [bold underline]http://{host}:{port}[/bold underline]\n"
            f"API Docs: http://{host}:{port}/docs",
            border_style="cyan",
        )
    )
    uvicorn.run(
        "hydrogen_team.server:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command(name="adk-web")
def adk_web(
    port: Annotated[int, typer.Option("--port", "-p", help="Port for native Google ADK Web UI")] = 8000,
    scenario: Annotated[str, typer.Option("--scenario", "-s", help="Scenario for native ADK root_agent")] = "video_vfx",
    mode: Annotated[str, typer.Option("--mode", "-m", help="Mode for native ADK root_agent")] = "peer_mesh",
) -> None:
    """Launch Google ADK's built-in developer UI pointed at `adk_agents/`."""
    adk_bin = shutil.which("adk")
    if not adk_bin:
        console.print("[red]Could not find `adk` CLI on PATH. Activate your virtualenv first.[/red]")
        raise typer.Exit(1)

    agents_dir = Path(__file__).resolve().parents[2] / "adk_agents"
    if not agents_dir.is_dir():
        agents_dir = Path.cwd() / "adk_agents"

    settings = get_settings()
    settings.apply_runtime_env()
    import os

    env = os.environ.copy()
    env["HYDROGEN_ADK_SCENARIO"] = scenario
    env["HYDROGEN_ADK_MODE"] = mode

    console.print(
        f"[cyan]Launching native Google ADK UI on http://127.0.0.1:{port} "
        f"(scenario={scenario}, mode={mode})...[/cyan]"
    )
    subprocess.run([adk_bin, "web", str(agents_dir), "--port", str(port)], env=env, check=False)


if __name__ == "__main__":
    app()
