"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useResearchStore, ValidationResults } from "@/stores/research-store";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import type { AgentEvent, ResearchStatus, Paper, Citation, Source } from "@/lib/types";

interface StatusPayload {
  status?: string;
  validation?: ValidationResults;
}

const STUCK_SESSION_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
const STUCK_CHECK_INTERVAL_MS = 10_000;

export function useResearch() {
  const store = useResearchStore();
  const { messages, isConnected, reconnecting, manualReconnect } = useWebSocket(store.sessionId);
  const processedRef = useRef(0);
  const [stuckDetected, setStuckDetected] = useState(false);
  const stuckTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [loading, setLoading] = useState(false);

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
    } catch (error) {
      // Paper might not be ready yet - log for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log('Paper not ready yet:', error);
      }
    }
  }, [store]);

  // Process incoming WebSocket messages
  useEffect(() => {
    if (messages.length <= processedRef.current) return;

    const newMessages = messages.slice(processedRef.current);
    processedRef.current = messages.length;
    setStuckDetected(false);

    for (const msg of newMessages) {
      if (msg.type === "agent_event") {
        const event = msg.data as AgentEvent;
        store.addEvent(event);

        // Extract sources from search events
        if (event.agent === "search" && event.type === "completed" && event.data?.results) {
          const results = event.data.results;
          store.setSources(Array.isArray(results) ? (results as unknown as Source[]) : []);
        }

        // Collect sources from browsing/reading events too
        if ((event.agent === "browser" || event.agent === "reader") && event.type === "completed" && event.data?.sources) {
          const srcs = event.data.sources as unknown as Source[];
          if (Array.isArray(srcs) && srcs.length > 0) {
            const existing = store.sources;
            const newUrls = new Set(existing.map(s => s.url));
            const merged = [...existing, ...srcs.filter(s => !newUrls.has(s.url))];
            store.setSources(merged);
          }
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
          store.setIsStreaming(false);
          fetchPaper(store.sessionId);
        }
      }

      // Handle streaming paper content
      if (msg.type === "paper_chunk") {
        const data = msg.data as { content?: string; done?: boolean };
        if (data.content) {
          // Auto-switch to paper tab on first chunk (before append)
          const isFirstChunk = store.streamingContent.length === 0;
          store.appendStreamingContent(data.content);
          store.setIsStreaming(true);
          if (isFirstChunk) {
            store.setActivePanel("paper");
          }
        }
        if (data.done) {
          store.setIsStreaming(false);
        }
      }
    }
  }, [messages, fetchPaper, store]);

  // Stuck session detection
  useEffect(() => {
    if (!store.isRunning) return;

    let lastActivity = Date.now();
    const interval = setInterval(() => {
      if (messages.length > 0) lastActivity = Date.now();
      const elapsed = Date.now() - lastActivity;
      if (elapsed > STUCK_SESSION_TIMEOUT_MS && store.isRunning) {
        setStuckDetected(true);
      }
    }, STUCK_CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [store.isRunning, messages.length]);

  // Reset stuck detection when activity resumes
  useEffect(() => {
    if (messages.length > 0) {
      if (stuckTimerRef.current) clearTimeout(stuckTimerRef.current);
      stuckTimerRef.current = setTimeout(() => setStuckDetected(false), 0);
      return () => {
        if (stuckTimerRef.current) clearTimeout(stuckTimerRef.current);
      };
    }
  }, [messages.length]);

  const recoverStuckSession = useCallback(() => {
    setStuckDetected(false);
    // Try to re-fetch session state
    if (store.sessionId) {
      setLoading(true);
      api.getSession(store.sessionId)
        .then((session) => {
          if (session) {
            if (session.status) {
              store.setStatus(session.status as ResearchStatus);
            }
            if (session.status === "completed") {
              fetchPaper(store.sessionId!);
            }
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
    manualReconnect();
  }, [store, fetchPaper, manualReconnect]);

  const restoreSession = useCallback(async (sessionId: string) => {
    setLoading(true);
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
          } catch {
            // Diagnostics endpoint may not be available
          }
        }
      }
    } catch (err) {
      console.error("Failed to restore session details", err);
      localStorage.removeItem("researchos_session_id");
      store.reset();
    } finally {
      setLoading(false);
    }
  }, [store, fetchPaper]);

  // Restore session on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem("researchos_session_id");
    if (savedSessionId && !store.sessionId) {
      store.setSessionId(savedSessionId);
      const timer = setTimeout(() => restoreSession(savedSessionId), 0);
      return () => clearTimeout(timer);
    }
  }, [restoreSession, store]);

  const startResearch = useCallback(
    async (prompt: string, depth: string, maxSources: number, pages?: number, layout?: string, font?: string, visualMode?: string) => {
      console.log("[DEBUG] START_RESEARCH_CALLED in useResearch", { prompt, depth, maxSources, pages, layout, font, visualMode });
      setLoading(true);
      store.reset();
      store.setPrompt(prompt);
      if (layout) store.setLayout(layout as "1 Column" | "2 Column" | "Multi Column");
      if (font) store.setFont(font);

      try {
        console.log("[DEBUG] API_REQUEST_SENT to /api/research");
        const res = await api.startResearch({
          prompt,
          depth,
          max_sources: maxSources,
          pages: pages || 12,
          layout: layout || "2 Column",
          font: font || "Times New Roman",
          visual_mode: visualMode || "Mixed",
        });
        console.log("[DEBUG] API_RESPONSE_RECEIVED", res);
        store.setSessionId(res.session_id);
        localStorage.setItem("researchos_session_id", res.session_id);
        store.setStatus("pending");
        processedRef.current = 0;
      } catch (err) {
        console.error("[DEBUG] API_ERROR", err);
        store.setStatus("failed");
      } finally {
        setLoading(false);
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
    reconnecting,
    stuckDetected,
    loading,
    startedAt: store.startedAt,
    completedAt: store.completedAt,
    totalTokensIn: store.totalTokensIn,
    totalTokensOut: store.totalTokensOut,
    totalCost: store.totalCost,
    streamingContent: store.streamingContent,
    isStreaming: store.isStreaming,

    // Actions
    startResearch,
    setActivePanel: store.setActivePanel,
    reset,
    recoverStuckSession,
  }
}