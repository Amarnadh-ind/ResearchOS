// ── Research Types ────────────────────────────────────

export type ResearchStatus =
  | "pending"
  | "planning"
  | "searching"
  | "browsing"
  | "reading"
  | "extracting"
  | "critiquing"
  | "analyzing_novelty"
  | "writing"
  | "citing"
  | "formatting"
  | "completed"
  | "failed";

export interface ResearchRequest {
  prompt: string;
  depth: "quick" | "standard" | "deep";
  max_sources: number;
  output_format: string;
}

export interface ResearchResponse {
  session_id: string;
  status: ResearchStatus;
  message: string;
}

export interface AgentEvent {
  agent: string;
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
  session_id?: string;
}

export interface WSMessage {
  type: "agent_event" | "status" | "pipeline_complete" | "paper_chunk" | "pong";
  data: AgentEvent | Record<string, unknown>;
}

export interface PipelineAgent {
  order: number;
  agent: string;
  description: string;
  status: "pending" | "running" | "completed" | "error" | "skipped";
  duration_ms?: number;
}

export interface PaperSection {
  heading: string;
  content: string;
  subsections?: PaperSection[];
}

export interface Paper {
  title: string;
  authors: string[];
  abstract: string;
  keywords: string[];
  sections: PaperSection[];
  references: string[];
  content_markdown: string;
}

export interface Citation {
  key: string;
  ieee_format: string;
  authors: string[];
  title: string;
  url: string;
  year?: number;
  verified: boolean;
}

export interface Source {
  url: string;
  title: string;
  snippet: string;
  relevance_score: number;
}

export const AGENT_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  planner: { label: "Planner", color: "var(--color-agent-planner)", icon: "🧠" },
  search: { label: "Search", color: "var(--color-agent-search)", icon: "🔍" },
  firecrawl_extract: { label: "Firecrawl Extract", color: "var(--color-agent-browser)", icon: "🌐" },
  reader: { label: "Reader", color: "var(--color-agent-reader)", icon: "📖" },
  claim_extractor: { label: "Claims", color: "var(--color-agent-claims)", icon: "⚡" },
  critic: { label: "Critic", color: "var(--color-agent-critic)", icon: "🔬" },
  novelty: { label: "Novelty", color: "var(--color-agent-novelty)", icon: "✨" },
  citation: { label: "Citation", color: "var(--color-agent-citation)", icon: "📝" },
  writer: { label: "Writer", color: "var(--color-agent-writer)", icon: "✍️" },
  ieee_formatter: { label: "IEEE", color: "var(--color-agent-ieee)", icon: "📄" },
  humanizer: { label: "Humanizer", color: "var(--color-agent-humanizer)", icon: "🎭" },
  page_validator: { label: "Validator", color: "var(--color-agent-validator)", icon: "🛡️" },
};

export const PIPELINE_ORDER = [
  "planner",
  "search",
  "firecrawl_extract",
  "reader",
  "claim_extractor",
  "critic",
  "novelty",
  "citation",
  "writer",
  "ieee_formatter",
  "humanizer",
  "page_validator",
];

export const STATUS_TO_AGENT: Record<string, string> = {
  planning: "planner",
  searching: "search",
  browsing: "firecrawl_extract",
  reading: "reader",
  extracting: "claim_extractor",
  critiquing: "critic",
  analyzing_novelty: "novelty",
  citing: "citation",
  writing: "writer",
  formatting: "ieee_formatter",
  humanizing: "humanizer",
  validating_pages: "page_validator",
};

// ── Pipeline Stages (user-facing progress) ─────────────

export interface PipelineStage {
  key: string;
  label: string;
  icon: string;
  agents: string[];
  parallel?: boolean;
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { key: "searching", label: "Searching", icon: "🔍", agents: ["planner", "search", "firecrawl_extract"] },
  { key: "reading", label: "Reading", icon: "📖", agents: ["reader", "claim_extractor"], parallel: true },
  { key: "writing", label: "Writing", icon: "✍️", agents: ["critic", "novelty", "writer"] },
  { key: "citing", label: "Citing", icon: "📝", agents: ["citation"] },
  { key: "formatting", label: "Formatting", icon: "📄", agents: ["ieee_formatter"] },
  { key: "humanizing", label: "Humanizing", icon: "🧠", agents: ["humanizer"] },
  { key: "exporting", label: "Exporting", icon: "📦", agents: ["page_validator"] },
];

export function getStageStatus(
  stage: PipelineStage,
  agents: PipelineAgent[]
): "pending" | "active" | "completed" | "error" {
  const stageAgents = agents.filter(a => stage.agents.includes(a.agent));
  if (stageAgents.length === 0) {
    return "pending";
  }
  if (stageAgents.some(a => a.status === "error")) return "error";
  
  const hasRunning = stageAgents.some(a => a.status === "running");
  const allDone = stageAgents.every(a => a.status === "completed" || a.status === "skipped");
  const someDone = stageAgents.some(a => a.status === "completed");
  
  if (stage.parallel) {
    if (hasRunning || someDone) return "active";
    if (allDone) return "completed";
    return "pending";
  }
  
  if (hasRunning) return "active";
  if (allDone) return "completed";
  if (someDone) return "active";
  return "pending";
}

export function getCurrentStageIndex(agents: PipelineAgent[]): number {
  for (let i = 0; i < PIPELINE_STAGES.length; i++) {
    const status = getStageStatus(PIPELINE_STAGES[i], agents);
    if (status === "active") return i;
    if (status === "pending") return i;
  }
  return PIPELINE_STAGES.length - 1;
}

// ── Model Health ───────────────────────────────────────

export interface ModelHealth {
  provider: string;
  displayName: string;
  status: "online" | "degraded" | "offline";
  latency?: number;
  model: string;
}
