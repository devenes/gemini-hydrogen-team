import { useEffect, useRef, useState } from "react";
import { Plus, RotateCcw, Trash2, X } from "lucide-react";
import type { AgentBlueprint } from "../types";

interface CustomSquadModalProps {
  open: boolean;
  defaultAgents: AgentBlueprint[];
  customAgents: AgentBlueprint[] | null;
  onSave: (agents: AgentBlueprint[] | null) => void;
  onClose: () => void;
}

export function CustomSquadModal({
  open,
  defaultAgents,
  customAgents,
  onSave,
  onClose,
}: CustomSquadModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState<AgentBlueprint[]>(customAgents ?? defaultAgents);

  useEffect(() => {
    if (open) {
      setDraft(customAgents ? structuredClone(customAgents) : structuredClone(defaultAgents));
    }
  }, [open, customAgents, defaultAgents]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  // Light-dismiss fallback for browsers without native `closedby="any"`
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

  const updateAgent = (idx: number, patch: Partial<AgentBlueprint>) => {
    setDraft((prev) => prev.map((a, i) => (i === idx ? { ...a, ...patch } : a)));
  };

  const addAgent = () => {
    const n = draft.length + 1;
    setDraft((prev) => [
      ...prev,
      {
        name: `HydrogenSpecialist${n}`,
        role: "Domain Specialist",
        specialty: "Analysis, synthesis, and workspace deliverable generation",
        instruction:
          "Read the Team Blackboard, contribute your domain expertise, save a workspace deliverable, and post your findings to teammates.",
        include_code_runner: true,
        include_video_tools: false,
        include_finance_tools: false,
      },
    ]);
  };

  const removeAgent = (idx: number) => {
    if (draft.length <= 2) return;
    setDraft((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleClose = () => {
    if (dialogRef.current) {
      dialogRef.current.returnValue = "";
    }
    onClose();
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="squad-dialog-title"
      onClose={handleClose}
      {...({ closedby: "any" } as Record<string, string>)}
    >
      <div className="dialog-header">
        <h1 id="squad-dialog-title" className="dialog-title">
          Customize Hydrogen Agent Squad
        </h1>
        <button
          type="button"
          className="btn"
          aria-label="Close squad customizer"
          onClick={() => dialogRef.current?.close()}
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      <div className="dialog-body">
        <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-secondary)" }}>
          Edit agent roles, instructions, or tool permissions — or add new specialists to create a
          bespoke Hydrogen Team squad.
        </p>

        {draft.map((agent, idx) => (
          <div key={idx} className="probe-card" style={{ gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <strong style={{ fontSize: 12.5 }}>Agent #{idx + 1}</strong>
              <button
                type="button"
                className="btn"
                disabled={draft.length <= 2}
                onClick={() => removeAgent(idx)}
                aria-label={`Remove ${agent.name}`}
                style={{ padding: "4px 8px" }}
              >
                <Trash2 size={13} aria-hidden="true" />
              </button>
            </div>

            <div className="two-col">
              <div>
                <label className="field-label" htmlFor={`agent-name-${idx}`}>
                  Identifier (No Spaces)
                </label>
                <input
                  id={`agent-name-${idx}`}
                  className="text-input"
                  value={agent.name}
                  onChange={(e) =>
                    updateAgent(idx, { name: e.target.value.replace(/[^A-Za-z0-9_]/g, "") })
                  }
                  autoFocus={idx === 0}
                />
              </div>
              <div>
                <label className="field-label" htmlFor={`agent-role-${idx}`}>
                  Role Title
                </label>
                <input
                  id={`agent-role-${idx}`}
                  className="text-input"
                  value={agent.role}
                  onChange={(e) => updateAgent(idx, { role: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="field-label" htmlFor={`agent-inst-${idx}`}>
                System Instruction
              </label>
              <textarea
                id={`agent-inst-${idx}`}
                className="text-input"
                rows={3}
                value={agent.instruction}
                onChange={(e) => updateAgent(idx, { instruction: e.target.value })}
              />
            </div>

            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={agent.include_code_runner}
                  onChange={(e) => updateAgent(idx, { include_code_runner: e.target.checked })}
                />
                Python Runner
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={agent.include_video_tools}
                  onChange={(e) => updateAgent(idx, { include_video_tools: e.target.checked })}
                />
                FFmpeg Video Renderer
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={agent.include_finance_tools}
                  onChange={(e) => updateAgent(idx, { include_finance_tools: e.target.checked })}
                />
                Financial Modeler
              </label>
            </div>
          </div>
        ))}

        <button type="button" className="btn" onClick={addAgent}>
          <Plus size={14} aria-hidden="true" />
          Add Hydrogen Specialist
        </button>
      </div>

      <div className="dialog-footer">
        <button
          type="button"
          className="btn"
          onClick={() => {
            onSave(null);
            dialogRef.current?.close();
          }}
        >
          <RotateCcw size={13} aria-hidden="true" />
          Reset to Scenario Defaults
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            const sanitized = draft.filter((a) => a.name.trim().length > 0);
            if (sanitized.length >= 2) {
              onSave(sanitized);
            }
            dialogRef.current?.close();
          }}
        >
          Apply Squad
        </button>
      </div>
    </dialog>
  );
}
