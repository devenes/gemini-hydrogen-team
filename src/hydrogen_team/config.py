"""Runtime configuration & zero-key Google Cloud Vertex AI ADC auto-detection."""

from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _run_gcloud_value(*args: str) -> str | None:
    """Safely query gcloud CLI configuration without raising if unavailable."""
    if not shutil.which("gcloud"):
        return None
    try:
        proc = subprocess.run(
            ["gcloud", *args],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if proc.returncode == 0:
            val = proc.stdout.strip()
            if val and val != "(unset)":
                return val
    except Exception:
        return None
    return None


@lru_cache(maxsize=1)
def detect_gcloud_project() -> str | None:
    return (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
        or _run_gcloud_value("config", "get-value", "project")
    )


@lru_cache(maxsize=1)
def detect_gcloud_account() -> str | None:
    return _run_gcloud_value("config", "get-value", "account")


def has_adc_credentials() -> bool:
    """Return True if Google Application Default Credentials are available."""
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).expanduser().is_file()
    adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    if adc_path.is_file():
        return True
    try:
        import google.auth

        creds, _ = google.auth.default()
        return creds is not None
    except Exception:
        return False


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_genai_use_vertexai: bool = Field(
        default=True,
        alias="GOOGLE_GENAI_USE_VERTEXAI",
    )
    google_cloud_project: str | None = Field(
        default=None,
        alias="GOOGLE_CLOUD_PROJECT",
    )
    google_cloud_location: str = Field(
        default="global",
        alias="GOOGLE_CLOUD_LOCATION",
    )
    gemini_api_key: str | None = Field(
        default=None,
        alias="GEMINI_API_KEY",
    )
    google_api_key: str | None = Field(
        default=None,
        alias="GOOGLE_API_KEY",
    )
    default_worker_model: str = Field(
        default="gemini-4-hydrogen",
        alias="HYDROGEN_WORKER_MODEL",
    )
    default_orchestrator_model: str = Field(
        default="gemini-4-argon",
        alias="HYDROGEN_ORCHESTRATOR_MODEL",
    )
    fallback_model: str = Field(
        default="gemini-2.5-flash",
        alias="HYDROGEN_FALLBACK_MODEL",
    )
    default_thinking_level: str = Field(
        default="MEDIUM",
        alias="HYDROGEN_THINKING_LEVEL",
    )
    runs_dir: Path = Field(
        default=Path("runs"),
        alias="HYDROGEN_RUNS_DIR",
    )
    host: str = Field(default="127.0.0.1", alias="HYDROGEN_HOST")
    port: int = Field(default=8042, alias="HYDROGEN_PORT")
    max_llm_calls: int = Field(default=40, alias="HYDROGEN_MAX_LLM_CALLS")

    @property
    def resolved_project(self) -> str | None:
        return self.google_cloud_project or detect_gcloud_project()

    @property
    def resolved_api_key(self) -> str | None:
        return self.gemini_api_key or self.google_api_key

    @property
    def auth_mode(self) -> Literal["vertex_adc", "gemini_api_key", "unconfigured"]:
        if self.google_genai_use_vertexai and self.resolved_project and has_adc_credentials():
            return "vertex_adc"
        if self.resolved_api_key:
            return "gemini_api_key"
        if self.google_genai_use_vertexai and self.resolved_project:
            return "vertex_adc"
        return "unconfigured"

    def apply_runtime_env(self) -> None:
        """Synchronize resolved Vertex AI / Gemini API settings into os.environ for Google ADK."""
        if self.auth_mode == "vertex_adc":
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
            if self.resolved_project:
                os.environ["GOOGLE_CLOUD_PROJECT"] = self.resolved_project
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.google_cloud_location or "global"
            # Avoid conflicting API keys when using Vertex AI ADC by default.
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)
        elif self.auth_mode == "gemini_api_key" and self.resolved_api_key:
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
            os.environ["GOOGLE_API_KEY"] = self.resolved_api_key
            os.environ["GEMINI_API_KEY"] = self.resolved_api_key


class EnvironmentStatus(BaseModel):
    auth_mode: Literal["vertex_adc", "gemini_api_key", "unconfigured"]
    gcp_project: str | None = None
    gcp_location: str = "global"
    gcp_account: str | None = None
    adc_available: bool = False
    api_key_configured: bool = False
    ffmpeg_available: bool = False
    python_version: str = ""
    adk_version: str = ""
    default_worker_model: str = "gemini-4-hydrogen"
    default_orchestrator_model: str = "gemini-4-neon"
    fallback_model: str = "gemini-2.5-flash"


def get_settings() -> Settings:
    settings = Settings()
    settings.runs_dir = settings.runs_dir.resolve()
    return settings


def inspect_environment(settings: Settings | None = None) -> EnvironmentStatus:
    import sys

    cfg = settings or get_settings()
    try:
        import google.adk as adk

        adk_ver = getattr(adk, "__version__", "installed")
    except Exception:
        adk_ver = "not installed"

    return EnvironmentStatus(
        auth_mode=cfg.auth_mode,
        gcp_project=cfg.resolved_project,
        gcp_location=cfg.google_cloud_location,
        gcp_account=detect_gcloud_account(),
        adc_available=has_adc_credentials(),
        api_key_configured=bool(cfg.resolved_api_key),
        ffmpeg_available=shutil.which("ffmpeg") is not None,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        adk_version=adk_ver,
        default_worker_model=cfg.default_worker_model,
        default_orchestrator_model=cfg.default_orchestrator_model,
        fallback_model=cfg.fallback_model,
    )
