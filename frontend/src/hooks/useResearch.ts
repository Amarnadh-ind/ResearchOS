"use client";

import { useCallback, useEffect, useRef } from "react";
import { useResearchStore, ValidationResults } from "@/stores/research-store";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import type { AgentEvent, ResearchStatus, Paper, Citation, Source } from "@/lib/types";

interface StatusPayload {
  status?: string;
  validation?: ValidationResults;
}

export function useResearch() {
  const store = useResearchStore();
  const { messages, isConnected } = useWebSocket(store.sessionId);
  const processedRef = useRef(0);

  const fetchPaper = useCallback(async (sessionId: string) => {
    try {
      const paper = await api.getPaper(sessionId) as unknown as Record<string, unknown>;
      if (paper) {
        store.setPaper(paper as unknown as Paper);
        store.setMarkdown((paper.content_markdown as string) || "");
        if (paper.citations) {
          store.setCitations(paper.citations as unknown as Citation[]);
        }
        store.setActivePanel("paper");
      }
    } catch {
      // Paper might not be ready yet
    }
  }, [store]);

  // Process incoming WebSocket messages
  useEffect(() => {
    if (messages.length <= processedRef.current) return;

    const newMessages = messages.slice(processedRef.current);
    processedRef.current = messages.length;

    for (const msg of newMessages) {
      if (msg.type === "agent_event") {
        const event = msg.data as AgentEvent;
        store.addEvent(event);

        // Extract sources from search events
        if (event.agent === "search" && event.type === "completed" && event.data?.results) {
          const results = event.data.results;
          store.setSources(Array.isArray(results) ? (results as unknown as Source[]) : []);
        }
      }

      if (msg.type === "status") {
        const data = msg.data as StatusPayload;
        if (data.status) {
          store.setStatus(data.status as ResearchStatus);
        }
        if (data.validation) {
          store.setValidation(data.validation);
        }
      }

      if (msg.type === "pipeline_complete") {
        const data = msg.data as StatusPayload;
        store.setStatus((data.status as ResearchStatus) || "completed");
        if (data.validation) {
          store.setValidation(data.validation);
        }

        // Fetch the paper
        if (store.sessionId && data.status === "completed") {
          fetchPaper(store.sessionId);
        }
      }
    }
  }, [messages, fetchPaper, store]);

  const restoreSession = useCallback(async (sessionId: string) => {
    try {
      const session = await api.getSession(sessionId);
      if (session) {
        store.setPrompt((session.prompt as string) || "");
        if (session.status) {
          store.setStatus(session.status as ResearchStatus);
        }
        if (session.validation) {
          store.setValidation(session.validation as ValidationResults);
        }
        
        // Rehydrate paper if completed
        if (session.status === "completed") {
          await fetchPaper(sessionId);
          
          // Fallback retrieval of sources and citations from diagnostics
          try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const diagRes = await fetch(`${API_URL}/api/research/${sessionId}/diagnostics`);
            if (diagRes.ok) {
              const diag = await diagRes.json();
              if (diag.search_results) {
                store.setSources(diag.search_results);
              }
              if (diag.citations_collected) {
                store.setCitations(diag.citations_collected);
              }
            }
          } catch (e) {
            console.error("Failed to restore sources/citations", e);
          }
        }
      }
    } catch (err) {
      console.error("Failed to restore session details", err);
      localStorage.removeItem("researchos_session_id");
      store.reset();
    }
  }, [store, fetchPaper]);

  // Restore session on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem("researchos_session_id");
    if (savedSessionId && !store.sessionId) {
      store.setSessionId(savedSessionId);
      restoreSession(savedSessionId);
    }
  }, [restoreSession, store]);

  const startResearch = useCallback(
    async (prompt: string, depth: string, maxSources: number, pages?: number, layout?: string, font?: string, visualMode?: string) => {
      store.reset();
      store.setPrompt(prompt);
      if (layout) store.setLayout(layout as "1 Column" | "2 Column" | "Multi Column");
      if (font) store.setFont(font);

      try {
        const res = await api.startResearch({
          prompt,
          depth,
          max_sources: maxSources,
          pages: pages || 12,
          layout: layout || "2 Column",
          font: font || "Times New Roman",
          visual_mode: visualMode || "Mixed",
        });
        store.setSessionId(res.session_id);
        localStorage.setItem("researchos_session_id", res.session_id);
        store.setStatus("pending");
        processedRef.current = 0;
      } catch {
        store.setStatus("failed");
      }
    },
    [store]
  );

  const reset = useCallback(() => {
    localStorage.removeItem("researchos_session_id");
    store.reset();
  }, [store]);

  return {
    // State
    sessionId: store.sessionId,
    prompt: store.prompt,
    status: store.status,
    isRunning: store.isRunning,
    error: store.error,
    agents: store.agents,
    events: store.events,
    currentAgent: store.currentAgent,
    sources: store.sources,
    claims: store.claims,
    paper: store.paper,
    citations: store.citations,
    markdown: store.markdown,
    activePanel: store.activePanel,
    isConnected,

    // Actions
    startResearch,
    setActivePanel: store.setActivePanel,
    reset,
  };
}