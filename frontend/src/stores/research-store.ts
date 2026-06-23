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

  // Timing & Completion
  startedAt: number | null;
  completedAt: number | null;
  agentTimings: Record<string, { started: number; completed?: number }>;

  // Token tracking
  totalTokensIn: number;
  totalTokensOut: number;
  totalCost: number;

  // Streaming paper
  streamingContent: string;
  isStreaming: boolean;

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
  addTokens: (tokensIn: number, tokensOut: number, cost: number) => void;
  appendStreamingContent: (chunk: string) => void;
  setStreamingContent: (content: string) => void;
  setIsStreaming: (streaming: boolean) => void;
  reset: () => void;
  getProgress: () => number;
  getRuntime: () => number | null;
  isComplete: () => boolean;
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

  startedAt: null,
  completedAt: null,
  agentTimings: {},

  totalTokensIn: 0,
  totalTokensOut: 0,
  totalCost: 0,

  streamingContent: "",
  isStreaming: false,

  setSessionId: (id) => set({ sessionId: id, isRunning: true, startedAt: Date.now() }),

  setPrompt: (prompt) => set({ prompt }),

  setStatus: (status) => {
    const currentAgentName = STATUS_TO_AGENT[status] || null;
    const state = get();
    const agents = state.agents.map((a) => {
      if (a.agent === currentAgentName) {
        return { ...a, status: "running" as const };
      }
      return a;
    });

    const agentTimings = { ...state.agentTimings };
    if (currentAgentName && !agentTimings[currentAgentName]) {
      agentTimings[currentAgentName] = { started: Date.now() };
    }

    const isComplete = status === "completed" || status === "failed";

    set({
      status,
      currentAgent: currentAgentName,
      agents,
      isRunning: !isComplete,
      error: status === "failed" ? "Pipeline failed" : null,
      completedAt: isComplete ? Date.now() : null,
      agentTimings,
    });
  },

  addEvent: (event) => {
    const state = get();
    const agents = state.agents.map((a) => {
      if (a.agent === event.agent) {
        const newStatus = event.type === "completed" ? "completed" :
                         event.type === "error" ? "error" :
                         event.type === "skipped" ? "skipped" : a.status;
        return { ...a, status: newStatus as PipelineAgent["status"] };
      }
      return a;
    });

    const agentTimings = { ...state.agentTimings };
    if (!agentTimings[event.agent]) {
      agentTimings[event.agent] = { started: Date.now() };
    }
    if (event.type === "completed" || event.type === "error") {
      agentTimings[event.agent] = {
        ...agentTimings[event.agent],
        completed: Date.now(),
      };
    }

    // Track tokens from event data
    const data = event.data || {};
    const tokensIn = (data.tokens_in as number) || 0;
    const tokensOut = (data.tokens_out as number) || 0;
    const tokenCount = (data.token_count as number) || 0;
    const cost = (data.cost as number) || 0;

    set((state) => ({
      events: [...state.events, event],
      agents,
      claims: event.data?.claims
        ? (event.data.claims as number)
        : state.claims,
      agentTimings,
      totalTokensIn: state.totalTokensIn + tokensIn,
      totalTokensOut: state.totalTokensOut + (tokenCount > 0 && tokensIn === 0 ? tokenCount : tokensOut),
      totalCost: state.totalCost + cost,
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

  addTokens: (tokensIn, tokensOut, cost) =>
    set((state) => ({
      totalTokensIn: state.totalTokensIn + tokensIn,
      totalTokensOut: state.totalTokensOut + tokensOut,
      totalCost: state.totalCost + cost,
    })),

  appendStreamingContent: (chunk) =>
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    })),

  setStreamingContent: (content) => set({ streamingContent: content }),
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),

  getProgress: () => {
    const agents = get().agents;
    const completed = agents.filter((a) => a.status === "completed" || a.status === "error" || a.status === "skipped").length;
    return Math.round((completed / agents.length) * 100);
  },

  getRuntime: () => {
    const { startedAt, completedAt } = get();
    if (!startedAt) return null;
    return (completedAt || Date.now()) - startedAt;
  },

  isComplete: () => {
    const status = get().status;
    return status === "completed" || status === "failed";
  },

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
      startedAt: null,
      completedAt: null,
      agentTimings: {},
      totalTokensIn: 0,
      totalTokensOut: 0,
      totalCost: 0,
      streamingContent: "",
      isStreaming: false,
    }),
}));
