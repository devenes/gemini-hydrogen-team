export type CollaborationMode = "peer_mesh" | "orchestrated" | "pipeline_loop";

export type EventKind =
  | "run_started"
  | "phase_changed"
  | "agent_started"
  | "agent_finished"
  | "thought"
  | "message"
  | "tool_call"
  | "tool_result"
  | "blackboard_post"
  | "artifact_created"
  | "handoff"
  | "usage"
  | "fallback_notice"
  | "run_completed"
  | "error";

export interface EnvironmentStatus {
  auth_mode: "vertex_adc" | "gemini_api_key" | "unconfigured";
  gcp_project: string | null;
  gcp_location: string;
  gcp_account: string | null;
  adc_available: boolean;
  api_key_configured: boolean;
  ffmpeg_available: boolean;
  python_version: string;
  adk_version: string;
  default_worker_model: string;
  default_orchestrator_model: string;
  fallback_model: string;
}

export interface ModelSpec {
  id: string;
  symbol: string;
  atomic_number: number;
  display_name: string;
  family: string;
  rank: "worker" | "orchestrator" | "flagship" | "fallback";
  tagline: string;
  description: string;
  input_price_per_1m: number;
  output_price_per_1m: number;
  context_window: number;
  thinking_levels: string[];
  accent_color: string;
  recommended_location: string;
}

export interface ModelProbeResult {
  model_id: string;
  symbol: string;
  display_name: string;
  available: boolean;
  latency_ms: number | null;
  error: string | null;
  checked_at: number;
}

export interface AgentBlueprint {
  name: string;
  role: string;
  specialty: string;
  instruction: string;
  include_code_runner: boolean;
  include_video_tools: boolean;
  include_finance_tools: boolean;
  thinking_level?: string | null;
}

export interface PromptTemplate {
  id: string;
  title: string;
  badge: string;
  prompt: string;
  expected_deliverables: string[];
}

export interface ScenarioSpec {
  id: string;
  name: string;
  category: string;
  icon: string;
  tagline: string;
  description: string;
  recommended_mode: CollaborationMode;
  recommended_orchestrator: string;
  agents: AgentBlueprint[];
  templates: PromptTemplate[];
}

export interface RosterMember {
  name: string;
  role: string;
  specialty: string;
  model: string;
  symbol: string;
  accent_color: string;
  is_orchestrator: boolean;
  thinking_level: string;
}

export interface AgentTelemetry {
  name: string;
  role: string;
  model: string;
  symbol: string;
  accent_color: string;
  is_orchestrator: boolean;
  status: "idle" | "thinking" | "acting" | "done" | "error";
  calls: number;
  tool_calls: number;
  blackboard_posts: number;
  artifacts_created: number;
  prompt_tokens: number;
  output_tokens: number;
  thoughts_tokens: number;
  cost_usd: number;
  last_activity: string;
}

export interface RunTelemetry {
  run_id: string;
  started_at: number;
  finished_at: number | null;
  phase: string;
  total_prompt_tokens: number;
  total_output_tokens: number;
  total_thoughts_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  estimated_savings_vs_neon_usd: number;
  total_tool_calls: number;
  total_blackboard_posts: number;
  total_artifacts: number;
  agents: Record<string, AgentTelemetry>;
}

export interface RunSummary {
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  prompt: string;
  mode: CollaborationMode;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  worker_model: string;
  orchestrator_model: string;
  resolved_worker_model: string;
  resolved_orchestrator_model: string;
  used_fallback: boolean;
  fallback_reason: string | null;
  created_at: number;
  finished_at: number | null;
  roster: RosterMember[];
  telemetry: RunTelemetry;
  final_output: string;
  error: string | null;
}

export interface TeamEvent {
  seq: number;
  run_id: string;
  timestamp: number;
  kind: EventKind;
  agent: string;
  target_agent?: string | null;
  model?: string | null;
  title: string;
  content: string;
  data: Record<string, unknown>;
}

export interface BlackboardEntry {
  seq: number;
  timestamp: number;
  author: string;
  to_agent: string;
  topic: string;
  kind: "proposal" | "finding" | "critique" | "decision" | "handoff" | "question";
  message: string;
}

export interface ArtifactInfo {
  path: string;
  name: string;
  size_bytes: number;
  mime_type: string;
  preview_kind: "html" | "video" | "image" | "markdown" | "code" | "json" | "csv" | "binary";
  updated_at: number;
  created_by: string;
}
