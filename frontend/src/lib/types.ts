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
  type: "agent_event" | "status" | "pipeline_complete";
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
  browser: { label: "Browser", color: "var(--color-agent-browser)", icon: "🌐" },
  reader: { label: "Reader", color: "var(--color-agent-reader)", icon: "📖" },
  claim_extractor: { label: "Claims", color: "var(--color-agent-claims)", icon: "⚡" },
  critic: { label: "Critic", color: "var(--color-agent-critic)", icon: "🔬" },
  novelty: { label: "Novelty", color: "var(--color-agent-novelty)", icon: "✨" },
  citation: { label: "Citation", color: "var(--color-agent-citation)", icon: "📝" },
  writer: { label: "Writer", color: "var(--color-agent-writer)", icon: "✍️" },
  ieee_formatter: { label: "IEEE", color: "var(--color-agent-ieee)", icon: "📄" },
};

export const PIPELINE_ORDER = [
  "planner",
  "search",
  "browser",
  "reader",
  "claim_extractor",
  "critic",
  "novelty",
  "citation",
  "writer",
  "ieee_formatter",
];

export const STATUS_TO_AGENT: Record<string, string> = {
  planning: "planner",
  searching: "search",
  browsing: "browser",
  reading: "reader",
  extracting: "claim_extractor",
  critiquing: "critic",
  analyzing_novelty: "novelty",
  citing: "citation",
  writing: "writer",
  formatting: "ieee_formatter",
};
