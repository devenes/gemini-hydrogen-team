import { useEffect, useState } from "react";
import { Copy, Download, ExternalLink, FileCode2, Film, Globe, Check } from "lucide-react";
import type { ArtifactInfo } from "../types";
import { SafeMarkdown } from "./SafeMarkdown";

interface DeliverablesPanelProps {
  runId: string | null;
  artifacts: ArtifactInfo[];
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function DeliverablesPanel({ runId, artifacts }: DeliverablesPanelProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string>("");
  const [loadingText, setLoadingText] = useState(false);
  const [showRawHtml, setShowRawHtml] = useState(false);
  const [copied, setCopied] = useState(false);

  // Auto-select the highest-impact deliverable first (video -> html -> markdown -> first file)
  useEffect(() => {
    if (artifacts.length === 0) {
      setSelectedPath(null);
      return;
    }
    if (selectedPath && artifacts.some((a) => a.path === selectedPath)) {
      return;
    }
    const preferred =
      artifacts.find((a) => a.preview_kind === "video") ??
      artifacts.find((a) => a.preview_kind === "html") ??
      artifacts.find((a) => a.preview_kind === "markdown") ??
      artifacts[0];
    setSelectedPath(preferred.path);
  }, [artifacts, selectedPath]);

  const active = artifacts.find((a) => a.path === selectedPath) ?? null;
  const artifactUrl =
    runId && active
      ? `/api/runs/${encodeURIComponent(runId)}/artifacts/${active.path
          .split("/")
          .map(encodeURIComponent)
          .join("/")}`
      : null;

  useEffect(() => {
    if (!active || !artifactUrl) {
      setTextContent("");
      return;
    }
    if (
      active.preview_kind === "video" ||
      active.preview_kind === "image" ||
      active.preview_kind === "binary"
    ) {
      setTextContent("");
      return;
    }
    let cancelled = false;
    setLoadingText(true);
    fetch(artifactUrl)
      .then((res) => res.text())
      .then((txt) => {
        if (!cancelled) setTextContent(txt);
      })
      .catch(() => {
        if (!cancelled) setTextContent("Unable to load file preview.");
      })
      .finally(() => {
        if (!cancelled) setLoadingText(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active, artifactUrl]);

  const handleCopy = async () => {
    if (!textContent) return;
    await navigator.clipboard.writeText(textContent);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  // Hide noisy intermediate frame sequences from top of list unless user expands
  const displayArtifacts = artifacts.filter(
    (a) => !a.path.startsWith("frames/") || a.path.endsWith("0001.png")
  );

  if (!runId || artifacts.length === 0) {
    return (
      <div className="empty-state">
        <Film size={28} aria-hidden="true" />
        <strong>No deliverables generated yet</strong>
        <p style={{ margin: 0, maxWidth: 420 }}>
          As Hydrogen agents write code, render MP4 videos, create HTML5 motion studios, or publish
          dashboards and itineraries, every artifact appears here with live preview.
        </p>
      </div>
    );
  }

  return (
    <div className="deliverables-layout">
      <div className="file-tree" role="listbox" aria-label="Workspace deliverables">
        <a
          href={`/api/runs/${encodeURIComponent(runId)}/download`}
          className="btn"
          style={{ textDecoration: "none", marginBottom: 6 }}
        >
          <Download size={14} aria-hidden="true" />
          Download ZIP ({artifacts.length})
        </a>

        {displayArtifacts.map((a) => (
          <button
            key={a.path}
            type="button"
            className={`file-item ${a.path === selectedPath ? "active" : ""}`}
            onClick={() => {
              setSelectedPath(a.path);
              setShowRawHtml(false);
            }}
          >
            <span className="file-item-name">{a.path}</span>
            <span className="file-item-meta">
              {a.preview_kind.toUpperCase()} • {formatBytes(a.size_bytes)} • {a.created_by}
            </span>
          </button>
        ))}
      </div>

      <div className="preview-pane">
        {active && artifactUrl && (
          <>
            <div className="preview-toolbar">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {active.preview_kind === "video" ? (
                  <Film size={16} aria-hidden="true" />
                ) : active.preview_kind === "html" ? (
                  <Globe size={16} aria-hidden="true" />
                ) : (
                  <FileCode2 size={16} aria-hidden="true" />
                )}
                <strong>{active.path}</strong>
                <span className="count-chip">{formatBytes(active.size_bytes)}</span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {active.preview_kind === "html" && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setShowRawHtml((v) => !v)}
                  >
                    {showRawHtml ? "Live Preview" : "View Source"}
                  </button>
                )}
                {textContent && (
                  <button type="button" className="btn" onClick={handleCopy}>
                    {copied ? <Check size={13} aria-hidden="true" /> : <Copy size={13} aria-hidden="true" />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                )}
                <a
                  href={artifactUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn"
                  style={{ textDecoration: "none" }}
                >
                  <ExternalLink size={13} aria-hidden="true" />
                  Open
                </a>
              </div>
            </div>

            {active.preview_kind === "video" && (
              <video
                key={artifactUrl}
                className="preview-video"
                src={artifactUrl}
                controls
                autoPlay
                muted
                loop
                playsInline
              />
            )}

            {active.preview_kind === "image" && (
              <img className="preview-image" src={artifactUrl} alt={active.name} />
            )}

            {active.preview_kind === "html" && !showRawHtml && (
              <iframe
                key={artifactUrl}
                title={`Live preview of ${active.path}`}
                className="preview-iframe"
                src={artifactUrl}
                sandbox="allow-scripts"
              />
            )}

            {active.preview_kind === "markdown" && !loadingText && (
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--bg-elevated)",
                  maxHeight: 500,
                  overflowY: "auto",
                }}
              >
                <SafeMarkdown content={textContent} />
              </div>
            )}

            {(active.preview_kind === "code" ||
              active.preview_kind === "json" ||
              active.preview_kind === "csv" ||
              (active.preview_kind === "html" && showRawHtml)) && (
              <pre className="code-snippet" style={{ maxHeight: 500, overflowY: "auto" }}>
                {loadingText ? "Loading file..." : textContent}
              </pre>
            )}
          </>
        )}
      </div>
    </div>
  );
}
