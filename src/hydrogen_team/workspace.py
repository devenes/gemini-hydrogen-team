"""Sandboxed per-run workspace, shared Team Blackboard, and deliverable artifact manager."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
import zipfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

BlackboardKind = Literal["proposal", "finding", "critique", "decision", "handoff", "question"]
ArtifactPreviewKind = Literal["html", "video", "image", "markdown", "code", "json", "csv", "binary"]


class BlackboardEntry(BaseModel):
    seq: int
    timestamp: float = Field(default_factory=time.time)
    author: str
    to_agent: str = "all"
    topic: str
    kind: BlackboardKind = "finding"
    message: str


class ArtifactInfo(BaseModel):
    path: str
    name: str
    size_bytes: int
    mime_type: str
    preview_kind: ArtifactPreviewKind
    updated_at: float
    created_by: str = "agent"


_CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".scss",
    ".sh",
    ".bash",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".glsl",
    ".wgsl",
    ".txt",
}


def classify_artifact(path: Path) -> tuple[str, ArtifactPreviewKind]:
    suffix = path.suffix.lower()
    mime, _ = mimetypes.guess_type(str(path))
    if suffix in {".html", ".htm"}:
        return mime or "text/html", "html"
    if suffix in {".mp4", ".webm", ".mov"}:
        return mime or "video/mp4", "video"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return mime or "image/png", "image"
    if suffix in {".md", ".markdown"}:
        return "text/markdown", "markdown"
    if suffix == ".json":
        return "application/json", "json"
    if suffix == ".csv":
        return "text/csv", "csv"
    if suffix in _CODE_EXTENSIONS:
        return mime or "text/plain", "code"
    return mime or "application/octet-stream", "binary"


class RunWorkspace:
    """Manages isolated workspace files, shared Team Blackboard, and event logs for one run."""

    def __init__(self, run_id: str, runs_root: Path) -> None:
        self.run_id = run_id
        self.run_dir = (runs_root / run_id).resolve()
        self.workspace_dir = (self.run_dir / "workspace").resolve()
        self.events_file = self.run_dir / "events.jsonl"
        self.blackboard_file = self.run_dir / "blackboard.json"
        self.metadata_file = self.run_dir / "metadata.json"

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._blackboard: list[BlackboardEntry] = []
        self._artifact_authors: dict[str, str] = {}

        if self.blackboard_file.exists():
            try:
                raw = json.loads(self.blackboard_file.read_text(encoding="utf-8"))
                self._blackboard = [BlackboardEntry.model_validate(item) for item in raw]
            except Exception:
                self._blackboard = []

    def resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve a path strictly inside `workspace_dir`, blocking traversal attacks."""
        cleaned = relative_path.strip().lstrip("/").replace("\\", "/")
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError("Path must be a non-empty relative file path inside the workspace.")
        candidate = (self.workspace_dir / cleaned).resolve()
        try:
            candidate.relative_to(self.workspace_dir)
        except ValueError as exc:
            raise ValueError(f"Path '{relative_path}' escapes the sandboxed run workspace.") from exc
        return candidate

    def write_text_file(self, relative_path: str, content: str, *, author: str = "agent") -> ArtifactInfo:
        target = self.resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            target.write_text(content, encoding="utf-8")
            rel = target.relative_to(self.workspace_dir).as_posix()
            self._artifact_authors[rel] = author
            return self._build_artifact_info(target)

    def read_text_file(self, relative_path: str, max_chars: int = 40_000) -> str:
        target = self.resolve_safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"Workspace file not found: {relative_path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n... [truncated {len(text) - max_chars} chars]"
        return text

    def register_generated_file(self, relative_path: str, *, author: str = "agent") -> ArtifactInfo:
        target = self.resolve_safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"Generated file not found: {relative_path}")
        with self._lock:
            rel = target.relative_to(self.workspace_dir).as_posix()
            self._artifact_authors[rel] = author
            return self._build_artifact_info(target)

    def _build_artifact_info(self, path: Path) -> ArtifactInfo:
        rel = path.relative_to(self.workspace_dir).as_posix()
        stat = path.stat()
        mime_type, preview_kind = classify_artifact(path)
        return ArtifactInfo(
            path=rel,
            name=path.name,
            size_bytes=stat.st_size,
            mime_type=mime_type,
            preview_kind=preview_kind,
            updated_at=stat.st_mtime,
            created_by=self._artifact_authors.get(rel, "agent"),
        )

    def list_artifacts(self) -> list[ArtifactInfo]:
        with self._lock:
            items: list[ArtifactInfo] = []
            for p in sorted(self.workspace_dir.rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith("."):
                    items.append(self._build_artifact_info(p))
            return items

    def post_blackboard(
        self,
        *,
        author: str,
        topic: str,
        message: str,
        to_agent: str = "all",
        kind: BlackboardKind = "finding",
    ) -> BlackboardEntry:
        with self._lock:
            entry = BlackboardEntry(
                seq=len(self._blackboard) + 1,
                author=author,
                to_agent=to_agent or "all",
                topic=topic.strip() or "update",
                kind=kind,
                message=message.strip(),
            )
            self._blackboard.append(entry)
            self.blackboard_file.write_text(
                json.dumps([e.model_dump() for e in self._blackboard], indent=2),
                encoding="utf-8",
            )
            return entry

    def read_blackboard(self, limit: int = 50) -> list[BlackboardEntry]:
        with self._lock:
            return list(self._blackboard[-limit:])

    def append_event_jsonl(self, event_dict: dict) -> None:
        with self._lock:
            with self.events_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event_dict, ensure_ascii=False) + "\n")

    def save_metadata(self, data: dict) -> None:
        with self._lock:
            self.metadata_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def build_zip_bundle(self) -> Path:
        zip_path = self.run_dir / f"hydrogen-team-{self.run_id}.zip"
        with self._lock:
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for artifact in self.list_artifacts():
                    full = self.resolve_safe_path(artifact.path)
                    zf.write(full, arcname=f"workspace/{artifact.path}")
                if self.blackboard_file.exists():
                    zf.write(self.blackboard_file, arcname="blackboard.json")
                if self.metadata_file.exists():
                    zf.write(self.metadata_file, arcname="metadata.json")
        return zip_path
