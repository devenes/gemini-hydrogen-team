"""Periodic-table Gemini 4 model registry, live availability probing, cost estimation & fallback."""

from __future__ import annotations

import asyncio
import time
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from hydrogen_team.config import Settings


class ModelSpec(BaseModel):
    """Metadata for a Gemini model in the Hydrogen Team catalog."""

    id: str
    symbol: str
    atomic_number: int
    display_name: str
    family: str
    rank: Literal["worker", "orchestrator", "flagship", "fallback"]
    tagline: str
    description: str
    input_price_per_1m: float
    output_price_per_1m: float
    context_window: int = 1_048_576
    thinking_levels: list[str] = Field(default_factory=lambda: ["LOW", "MEDIUM", "HIGH"])
    accent_color: str
    recommended_location: str = "global"


MODEL_REGISTRY: dict[str, ModelSpec] = {
    "gemini-4-hydrogen": ModelSpec(
        id="gemini-4-hydrogen",
        symbol="H",
        atomic_number=1,
        display_name="Gemini 4 Hydrogen",
        family="Gemini 4",
        rank="worker",
        tagline="Fast, high-efficiency execution engine",
        description=(
            "Built for high-throughput parallel agents, rapid coding, motion graphics "
            "generation, and responsive collaboration at a fraction of flagship cost."
        ),
        input_price_per_1m=1.50,
        output_price_per_1m=7.50,
        thinking_levels=["MINIMAL", "LOW", "MEDIUM", "HIGH", "XHIGH"],
        accent_color="#38bdf8",
    ),
    "gemini-4-neon": ModelSpec(
        id="gemini-4-neon",
        symbol="Ne",
        atomic_number=10,
        display_name="Gemini 4 Neon",
        family="Gemini 4",
        rank="orchestrator",
        tagline="Balanced frontier workhorse & team lead",
        description=(
            "Ideal rank-up orchestrator: combines strong architectural synthesis with fast "
            "delegation across Hydrogen worker squads."
        ),
        input_price_per_1m=3.00,
        output_price_per_1m=15.00,
        thinking_levels=["LOW", "MEDIUM", "HIGH", "XHIGH"],
        accent_color="#f472b6",
    ),
    "gemini-4-argon": ModelSpec(
        id="gemini-4-argon",
        symbol="Ar",
        atomic_number=18,
        display_name="Gemini 4 Argon",
        family="Gemini 4",
        rank="orchestrator",
        tagline="Token-efficient deep reasoner & critic",
        description=(
            "Excels as a disciplined peer reviewer, security auditor, or orchestration lead "
            "with crisp long-horizon reasoning."
        ),
        input_price_per_1m=2.00,
        output_price_per_1m=10.00,
        thinking_levels=["LOW", "MEDIUM", "HIGH"],
        accent_color="#a78bfa",
    ),
    "gemini-4-carbon": ModelSpec(
        id="gemini-4-carbon",
        symbol="C",
        atomic_number=6,
        display_name="Gemini 4 Carbon",
        family="Gemini 4",
        rank="flagship",
        tagline="Heavy flagship deep reasoning specialist",
        description=(
            "Maximum reasoning depth for high-stakes strategic planning, complex systems "
            "architecture, and multi-team orchestration."
        ),
        input_price_per_1m=2.00,
        output_price_per_1m=10.00,
        thinking_levels=["LOW", "MEDIUM", "HIGH"],
        accent_color="#fbbf24",
    ),
    "gemini-2.5-flash": ModelSpec(
        id="gemini-2.5-flash",
        symbol="Fl",
        atomic_number=25,
        display_name="Gemini 2.5 Flash",
        family="Gemini 2.5",
        rank="fallback",
        tagline="Universal automatic fallback model",
        description=(
            "Automatically activated if Gemini 4 Hydrogen is not yet enabled on the user's "
            "Google Cloud project or Gemini API key."
        ),
        input_price_per_1m=0.15,
        output_price_per_1m=0.60,
        thinking_levels=["LOW", "MEDIUM", "HIGH"],
        accent_color="#34d399",
    ),
}


class ModelProbeResult(BaseModel):
    model_id: str
    symbol: str
    display_name: str
    available: bool
    latency_ms: int | None = None
    error: str | None = None
    checked_at: float = Field(default_factory=time.time)


class ModelResolution(BaseModel):
    requested_model: str
    resolved_model: str
    used_fallback: bool = False
    reason: str | None = None


_PROBE_CACHE: dict[str, ModelProbeResult] = {}
_PROBE_TTL_SECONDS = 300.0


def get_model_spec(model_id: str) -> ModelSpec:
    if model_id in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_id]
    return ModelSpec(
        id=model_id,
        symbol="Gm",
        atomic_number=0,
        display_name=model_id,
        family="Custom",
        rank="worker",
        tagline="Custom Gemini model",
        description=f"User-configured Gemini model ({model_id}).",
        input_price_per_1m=1.50,
        output_price_per_1m=7.50,
        accent_color="#60a5fa",
    )


def list_models() -> list[ModelSpec]:
    return list(MODEL_REGISTRY.values())


def estimate_cost_usd(
    model_id: str,
    prompt_tokens: int,
    output_tokens: int,
    thoughts_tokens: int = 0,
) -> float:
    """Estimate USD cost. Thinking tokens are billed at the model's output token rate."""
    spec = get_model_spec(model_id)
    in_cost = (max(prompt_tokens, 0) / 1_000_000.0) * spec.input_price_per_1m
    out_cost = (max(output_tokens + thoughts_tokens, 0) / 1_000_000.0) * spec.output_price_per_1m
    return round(in_cost + out_cost, 6)


def estimate_flagship_savings_usd(
    actual_cost_usd: float,
    total_prompt_tokens: int,
    total_output_tokens: int,
    total_thoughts_tokens: int,
    baseline_model_id: str = "gemini-4-neon",
) -> float:
    """Compare actual multi-agent cost against running every agent on a higher-tier model."""
    baseline = estimate_cost_usd(
        baseline_model_id,
        total_prompt_tokens,
        total_output_tokens,
        total_thoughts_tokens,
    )
    return round(max(baseline - actual_cost_usd, 0.0), 6)


def _create_genai_client(settings: Settings, *, timeout_ms: int = 25_000) -> genai.Client:
    http_opts_kwargs: dict[str, object] = {"timeout": timeout_ms}
    if hasattr(types, "HttpRetryOptions"):
        http_opts_kwargs["retry_options"] = types.HttpRetryOptions(attempts=1)
    http_opts = types.HttpOptions(**http_opts_kwargs)  # type: ignore[arg-type]

    if settings.auth_mode == "vertex_adc":
        return genai.Client(
            vertexai=True,
            project=settings.resolved_project,
            location=settings.google_cloud_location or "global",
            http_options=http_opts,
        )
    if settings.auth_mode == "gemini_api_key" and settings.resolved_api_key:
        return genai.Client(api_key=settings.resolved_api_key, http_options=http_opts)
    raise RuntimeError(
        "No Google Cloud ADC or GEMINI_API_KEY configured. "
        "Run `gcloud auth application-default login` or set GEMINI_API_KEY."
    )


async def _async_probe_model(model_id: str, settings: Settings, timeout_ms: int = 20_000) -> ModelProbeResult:
    spec = get_model_spec(model_id)
    start = time.perf_counter()
    try:
        client = _create_genai_client(settings, timeout_ms=timeout_ms)
        # Keep probes lightweight and compatible across Gemini 4 and Gemini 2.5 models.
        if model_id.startswith("gemini-4") or model_id.startswith("gemini-3"):
            config = types.GenerateContentConfig(max_output_tokens=256)
        else:
            config = types.GenerateContentConfig(
                max_output_tokens=128,
                thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0),
            )
        await client.aio.models.generate_content(
            model=model_id,
            contents="Reply with OK.",
            config=config,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ModelProbeResult(
            model_id=model_id,
            symbol=spec.symbol,
            display_name=spec.display_name,
            available=True,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        msg = str(exc).strip().splitlines()[0][:240]
        return ModelProbeResult(
            model_id=model_id,
            symbol=spec.symbol,
            display_name=spec.display_name,
            available=False,
            latency_ms=latency_ms,
            error=msg,
        )


async def probe_model(
    model_id: str,
    settings: Settings,
    *,
    force_refresh: bool = False,
    timeout_seconds: float = 20.0,
) -> ModelProbeResult:
    cached = _PROBE_CACHE.get(model_id)
    if (
        cached
        and not force_refresh
        and (time.time() - cached.checked_at) < _PROBE_TTL_SECONDS
    ):
        return cached
    try:
        result = await asyncio.wait_for(
            _async_probe_model(model_id, settings, timeout_ms=int(timeout_seconds * 1000)),
            timeout=timeout_seconds + 2.0,
        )
    except TimeoutError:
        spec = get_model_spec(model_id)
        result = ModelProbeResult(
            model_id=model_id,
            symbol=spec.symbol,
            display_name=spec.display_name,
            available=False,
            latency_ms=int(timeout_seconds * 1000),
            error="Timed out probing endpoint",
        )
    _PROBE_CACHE[model_id] = result
    return result


async def probe_all_models(
    settings: Settings,
    *,
    force_refresh: bool = False,
) -> list[ModelProbeResult]:
    tasks = [
        probe_model(model_id, settings, force_refresh=force_refresh)
        for model_id in MODEL_REGISTRY
    ]
    return list(await asyncio.gather(*tasks))


async def resolve_model_with_fallback(
    requested_model: str,
    settings: Settings,
    *,
    auto_fallback: bool = True,
) -> ModelResolution:
    """Verify whether requested_model works; gracefully fall back to Gemini Flash if unavailable."""
    if not auto_fallback:
        return ModelResolution(
            requested_model=requested_model,
            resolved_model=requested_model,
            used_fallback=False,
        )

    probe = await probe_model(requested_model, settings)
    if probe.available:
        return ModelResolution(
            requested_model=requested_model,
            resolved_model=requested_model,
            used_fallback=False,
        )

    fallback_id = settings.fallback_model
    if fallback_id != requested_model:
        fb_probe = await probe_model(fallback_id, settings)
        if fb_probe.available:
            return ModelResolution(
                requested_model=requested_model,
                resolved_model=fallback_id,
                used_fallback=True,
                reason=(
                    f"{requested_model} unavailable ({probe.error or 'access denied'}); "
                    f"automatically fell back to {fallback_id}."
                ),
            )

    return ModelResolution(
        requested_model=requested_model,
        resolved_model=requested_model,
        used_fallback=False,
        reason=probe.error,
    )


def clear_probe_cache() -> None:
    _PROBE_CACHE.clear()
