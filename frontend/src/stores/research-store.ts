"use client";

import { create } from "zustand";
import type {
  ResearchStatus,
  AgentEvent,
  Paper,
  Source,
  Citation,
  PipelineAgent,
} from "@/lib/types";
import { PIPELINE_ORDER, STATUS_TO_AGENT } from "@/lib/types";

export interface ValidationResults {
  page_count_achieved: boolean;
  actual_pages: number;
  requested_pages: number;
  topic_relevance_passed: boolean;
  relevance_score: number;
  sources_met: boolean;
  actual_sources: number;
  min_sources: number;
  citation_coverage_passed: boolean;
  cited_paragraphs: number;
  total_paragraphs: number;
  ieee_formatting_passed: boolean;
  validation_passed: boolean;
}

interface ResearchState {
  // Session
  sessionId: string | null;
  prompt: string;
  status: ResearchStatus | null;
  error: string | null;
  validation: ValidationResults | null;

  // Pipeline
  agents: PipelineAgent[];
  events: AgentEvent[];
  currentAgent: string | null;

  // Results
  sources: Source[];
  claims: number;
  paper: Paper | null;
  citations: Citation[];
  markdown: string;
  layout: "1 Column" | "2 Column" | "Multi Column";
  font: string;

  // UI
  activePanel: "stream" | "sources" | "graph" | "paper" | "citations" | "logs" | "diagnostics";
  isRunning: boolean;

  // Actions
  setSessionId: (id: string) => void;
  setPrompt: (prompt: string) => void;
  setStatus: (status: ResearchStatus) => void;
  addEvent: (event: AgentEvent) => void;
  updateAgentStatus: (agent: string, status: PipelineAgent["status"]) => void;
  setPaper: (paper: Paper) => void;
  setMarkdown: (md: string) => void;
  setLayout: (layout: "1 Column" | "2 Column" | "Multi Column") => void;
  setFont: (font: string) => void;
  setActivePanel: (panel: ResearchState["activePanel"]) => void;
  setSources: (sources: Source[]) => void;
  setCitations: (citations: Citation[]) => void;
  setValidation: (validation: ValidationResults | null) => void;
  reset: () => void;
}

const initialAgents: PipelineAgent[] = PIPELINE_ORDER.map((agent, i) => ({
  order: i + 1,
  agent,
  description: "",
  status: "pending" as const,
}));

export const useResearchStore = create<ResearchState>((set, get) => ({
  sessionId: null,
  prompt: "",
  status: null,
  error: null,
  validation: null,

  agents: [...initialAgents],
  events: [],
  currentAgent: null,

  sources: [],
  claims: 0,
  paper: null,
  citations: [],
  markdown: "",
  layout: "2 Column",
  font: "Times New Roman",

  activePanel: "stream",
  isRunning: false,

  setSessionId: (id) => set({ sessionId: id, isRunning: true }),

  setPrompt: (prompt) => set({ prompt }),

  setStatus: (status) => {
    const currentAgentName = STATUS_TO_AGENT[status] || null;
    const agents = get().agents.map((a) => {
      if (a.agent === currentAgentName) {
        return { ...a, status: "running" as const };
      }
      return a;
    });

    set({
      status,
      currentAgent: currentAgentName,
      agents,
      isRunning: status !== "completed" && status !== "failed",
      error: status === "failed" ? "Pipeline failed" : null,
    });
  },

  addEvent: (event) => {
    const agents = get().agents.map((a) => {
      if (a.agent === event.agent) {
        const newStatus = event.type === "completed" ? "completed" :
                         event.type === "error" ? "error" :
                         event.type === "skipped" ? "skipped" : a.status;
        return { ...a, status: newStatus as PipelineAgent["status"] };
      }
      return a;
    });

    set((state) => ({
      events: [...state.events, event],
      agents,
      claims: event.data?.claims
        ? (event.data.claims as number)
        : state.claims,
    }));
  },

  updateAgentStatus: (agent, status) => {
    set((state) => ({
      agents: state.agents.map((a) =>
        a.agent === agent ? { ...a, status } : a
      ),
    }));
  },

  setPaper: (paper) => set({ paper }),
  setMarkdown: (md) => set({ markdown: md }),
  setLayout: (layout) => set({ layout }),
  setFont: (font) => set({ font }),
  setActivePanel: (panel) => set({ activePanel: panel }),
  setSources: (sources) => set({ sources: Array.isArray(sources) ? sources : [] }),
  setCitations: (citations) => set({ citations: Array.isArray(citations) ? citations : [] }),
  setValidation: (validation) => set({ validation }),

  reset: () =>
    set({
      sessionId: null,
      prompt: "",
      status: null,
      error: null,
      validation: null,
      agents: [...initialAgents],
      events: [],
      currentAgent: null,
      sources: [],
      claims: 0,
      paper: null,
      citations: [],
      markdown: "",
      layout: "2 Column",
      font: "Times New Roman",
      activePanel: "stream",
      isRunning: false,
    }),
}));
