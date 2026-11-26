"""Unit tests for Periodic Table model catalog, cost calculations, and automatic fallback."""

from __future__ import annotations

import pytest

from hydrogen_team.config import Settings, inspect_environment
from hydrogen_team.models import (
    ModelProbeResult,
    clear_probe_cache,
    estimate_cost_usd,
    estimate_flagship_savings_usd,
    get_model_spec,
    list_models,
    resolve_model_with_fallback,
)


def test_periodic_table_catalog_has_all_gemini_4_elements():
    ids = {m.id for m in list_models()}
    assert {
        "gemini-4-hydrogen",
        "gemini-4-neon",
        "gemini-4-argon",
        "gemini-4-carbon",
        "gemini-2.5-flash",
    }.issubset(ids)

    h = get_model_spec("gemini-4-hydrogen")
    assert h.symbol == "H"
    assert h.atomic_number == 1
    assert "XHIGH" in h.thinking_levels


def test_cost_and_hydrogen_savings_math():
    h_cost = estimate_cost_usd("gemini-4-hydrogen", 100_000, 20_000, 30_000)
    # 0.1M * 1.50 + 0.05M * 7.50 = 0.15 + 0.375 = 0.525
    assert h_cost == pytest.approx(0.525, rel=1e-4)

    savings = estimate_flagship_savings_usd(h_cost, 100_000, 20_000, 30_000, "gemini-4-neon")
    # Neon cost = 0.1M * 3.00 + 0.05M * 15.00 = 0.30 + 0.75 = 1.05 -> savings = 0.525
    assert savings == pytest.approx(0.525, rel=1e-4)


async def test_auto_fallback_to_flash_when_hydrogen_unavailable(monkeypatch):
    clear_probe_cache()

    async def fake_probe(model_id: str, settings: Settings, **kwargs):
        if model_id == "gemini-4-hydrogen":
            return ModelProbeResult(
                model_id=model_id,
                symbol="H",
                display_name="Gemini 4 Hydrogen",
                available=False,
                error="404 NOT_FOUND",
            )
        return ModelProbeResult(
            model_id=model_id,
            symbol="Fl",
            display_name="Gemini 2.5 Flash",
            available=True,
            latency_ms=120,
        )

    monkeypatch.setattr("hydrogen_team.models.probe_model", fake_probe)
    settings = Settings()
    res = await resolve_model_with_fallback("gemini-4-hydrogen", settings, auto_fallback=True)
    assert res.used_fallback is True
    assert res.resolved_model == "gemini-2.5-flash"
    assert "404 NOT_FOUND" in (res.reason or "")


def test_inspect_environment_reports_runtime():
    status = inspect_environment(Settings())
    assert status.python_version != ""
    assert status.default_worker_model == "gemini-4-hydrogen"
