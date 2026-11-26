import { useEffect, useRef } from "react";
import { RefreshCw, X, CheckCircle2, XCircle } from "lucide-react";
import type { EnvironmentStatus, ModelProbeResult, ModelSpec } from "../types";

interface DoctorModalProps {
  open: boolean;
  environment: EnvironmentStatus | null;
  models: ModelSpec[];
  probeResults: ModelProbeResult[];
  probing: boolean;
  onProbe: (force: boolean) => void;
  onClose: () => void;
}

export function DoctorModal({
  open,
  environment,
  models,
  probeResults,
  probing,
  onProbe,
  onClose,
}: DoctorModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  // Light-dismiss fallback for browsers without native `closedby="any"` (per modern-web-guidance `dialog`)
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || "closedBy" in HTMLDialogElement.prototype) return;

    const outside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    let pressedOutside = false;
    const onDown = (e: PointerEvent) => {
      pressedOutside = outside(e);
    };
    const onUp = (e: PointerEvent) => {
      if (pressedOutside && outside(e)) dialog.close();
    };
    dialog.addEventListener("pointerdown", onDown);
    dialog.addEventListener("pointerup", onUp);
    return () => {
      dialog.removeEventListener("pointerdown", onDown);
      dialog.removeEventListener("pointerup", onUp);
    };
  }, []);

  const handleClose = () => {
    if (dialogRef.current) {
      dialogRef.current.returnValue = "";
    }
    onClose();
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="doctor-dialog-title"
      onClose={handleClose}
      {...({ closedby: "any" } as Record<string, string>)}
    >
      <div className="dialog-header">
        <h1 id="doctor-dialog-title" className="dialog-title">
          GCP Vertex AI Auth &amp; Gemini 4 Model Matrix
        </h1>
        <button
          type="button"
          className="btn"
          aria-label="Close diagnostics dialog"
          onClick={() => dialogRef.current?.close()}
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      <div className="dialog-body">
        {environment && (
          <div className="probe-grid">
            <div className="probe-card">
              <span className="metric-label">Authentication Mode</span>
              <strong>{environment.auth_mode}</strong>
              <span className="metric-sub">
                Project: {environment.gcp_project ?? "Not detected"} • Location: {environment.gcp_location}
              </span>
            </div>
            <div className="probe-card">
              <span className="metric-label">Runtime Tooling</span>
              <strong>Google ADK {environment.adk_version}</strong>
              <span className="metric-sub">
                Python {environment.python_version} • FFmpeg{" "}
                {environment.ffmpeg_available ? "Installed ✓" : "Not found"}
              </span>
            </div>
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <strong style={{ fontSize: 13 }}>Periodic Table Live Availability</strong>
          <button
            type="button"
            className="btn"
            disabled={probing}
            onClick={() => onProbe(true)}
            autoFocus
          >
            <RefreshCw size={13} aria-hidden="true" />
            {probing ? "Probing Vertex AI..." : "Re-Probe All Models"}
          </button>
        </div>

        <div className="probe-grid">
          {models.map((m) => {
            const res = probeResults.find((r) => r.model_id === m.id);
            return (
              <div key={m.id} className="probe-card">
                <div className="probe-head">
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="element-pill" style={{ color: m.accent_color }}>
                      {m.symbol}
                    </span>
                    <div>
                      <strong style={{ display: "block", fontSize: 13 }}>{m.display_name}</strong>
                      <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                        {m.id}
                      </span>
                    </div>
                  </div>
                  {res ? (
                    res.available ? (
                      <CheckCircle2 size={18} color="var(--accent-flash)" aria-label="Available" />
                    ) : (
                      <XCircle size={18} color="var(--accent-danger)" aria-label="Unavailable" />
                    )
                  ) : null}
                </div>
                <span className="metric-sub">
                  ${m.input_price_per_1m.toFixed(2)} / ${m.output_price_per_1m.toFixed(2)} per 1M tok
                  {res?.latency_ms ? ` • ${res.latency_ms}ms` : ""}
                </span>
                {res?.error && (
                  <span style={{ fontSize: 11, color: "var(--accent-danger)" }}>{res.error}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="dialog-footer">
        <form method="dialog">
          <button value="close" className="btn btn-primary">
            Done
          </button>
        </form>
      </div>
    </dialog>
  );
}
