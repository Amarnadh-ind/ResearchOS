"use client";

import { useState } from "react";
import { useResearchStore } from "@/stores/research-store";
import { Terminal, ChevronLeft, ChevronRight, Cpu, FileText, Globe, BookOpen, Key } from "lucide-react";
import { AGENT_CONFIG } from "@/lib/types";

export function DebugPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const { currentAgent, events, sources: rawSources, citations: rawCitations, prompt } = useResearchStore();
  const sources = Array.isArray(rawSources) ? rawSources : [];
  const citations = Array.isArray(rawCitations) ? rawCitations : [];

  // Find latest debug event
  const debugEvents = events.filter(e => e.type === "debug");
  const latestDebug = debugEvents.length > 0 ? debugEvents[debugEvents.length - 1] : null;

  const activeAgentConfig = currentAgent ? AGENT_CONFIG[currentAgent] : null;

  // Extract fields from latest debug event if available
  const debugData = latestDebug?.data as Record<string, unknown> | undefined;
  const currentTopic = (debugData?.topic as string) || prompt || "Autonomous Multi-Agent Systems";
  const currentPrompt = (debugData?.prompt as string) || "";
  const currentResponse = (debugData?.response as string) || "";

  return (
    <div className="relative h-full flex shrink-0 z-40">
      {/* Collapsed Toggle Button (vertical bar) */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute top-1/2 -left-8 transform -translate-y-1/2 w-8 h-32 rounded-l-xl bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-hover)] border-l border-y border-[var(--color-border)] flex flex-col items-center justify-center gap-2 text-[var(--color-text-muted)] hover:text-white transition-colors shadow-lg cursor-pointer"
      >
        {isOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        <Terminal className="w-4 h-4 rotate-90" />
        <span className="text-[9px] uppercase font-bold tracking-wider vertical-text select-none">
          Debug
        </span>
      </button>

      {/* Expanded Debug Panel */}
      <div
        className={`h-full bg-[var(--color-bg-secondary)] border-l border-[var(--color-border)] transition-all duration-300 flex flex-col overflow-hidden shadow-2xl ${
          isOpen ? "w-[400px]" : "w-0 border-l-0"
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-[var(--color-accent)] animate-pulse" />
            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Admin Live Debug Panel</h3>
          </div>
          <span className="text-[10px] bg-[var(--color-accent)]/15 text-[var(--color-accent)] px-2 py-0.5 rounded font-mono font-bold">
            LIVE
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 text-xs">
          {/* Item 1: Current Topic */}
          <div className="p-3 bg-[var(--color-bg-tertiary)]/50 border border-[var(--color-border)] rounded-lg">
            <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider block mb-1">
              Current Topic
            </span>
            <span className="font-semibold text-[var(--color-text-primary)]">{currentTopic}</span>
          </div>

          {/* Item 2: Current Agent */}
          <div className="p-3 bg-[var(--color-bg-tertiary)]/50 border border-[var(--color-border)] rounded-lg flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider block mb-1">
                Current Agent
              </span>
              <span className="font-semibold text-[var(--color-text-primary)] capitalize">
                {currentAgent ? currentAgent.replace("_", " ") : "Idle"}
              </span>
            </div>
            {activeAgentConfig && (
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-base shadow-md"
                style={{ backgroundColor: `${activeAgentConfig.color}20`, border: `1px solid ${activeAgentConfig.color}40` }}
              >
                {activeAgentConfig.icon}
              </div>
            )}
          </div>

          {/* Item 3: Current Prompt */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5 text-[var(--color-accent)]" />
              Current Prompt
            </span>
            <div className="h-32 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg font-mono text-[10px] text-[var(--color-text-secondary)] whitespace-pre-wrap">
              {currentPrompt || "No prompt payload in current agent step."}
            </div>
          </div>

          {/* Item 4: Current LLM Response */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider flex items-center gap-1">
              <FileText className="w-3.5 h-3.5 text-[var(--color-success)]" />
              Current LLM Response
            </span>
            <div className="h-44 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg font-mono text-[10px] text-[var(--color-text-primary)] whitespace-pre-wrap">
              {currentResponse || "Waiting for active LLM generation response..."}
            </div>
          </div>

          {/* Item 5: Current Sources */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text(--color-text-muted) tracking-wider flex items-center justify-between gap-1">
              <span className="flex items-center gap-1">
                <Globe className="w-3.5 h-3.5 text-[var(--color-info)]" />
                Current Sources
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">({sources.length})</span>
            </span>
            <div className="max-h-28 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg flex flex-col gap-1.5">
              {sources.length === 0 ? (
                <span className="text-[10px] text-[var(--color-text-muted)] italic">No sources collected yet.</span>
              ) : (
                sources.map((s, idx) => (
                  <div key={idx} className="flex flex-col pb-1.5 border-b border-[var(--color-border)] last:border-b-0">
                    <span className="font-semibold text-[10px] text-[var(--color-text-primary)] truncate">{s.title || "Untitled Source"}</span>
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-[9px] text-[var(--color-accent)] truncate hover:underline">
                      {s.url}
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Item 6: Current Citations */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text(--color-text-muted) tracking-wider flex items-center justify-between gap-1">
              <span className="flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5 text-[var(--color-warning)]" />
                Current Citations
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">({citations.length})</span>
            </span>
            <div className="max-h-28 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg flex flex-col gap-1">
              {citations.length === 0 ? (
                <span className="text-[10px] text-[var(--color-text-muted)] italic">No citations verified yet.</span>
              ) : (
                citations.map((c, idx) => (
                  <div key={idx} className="flex items-start gap-1 text-[10px] text-[var(--color-text-secondary)]">
                    <Key className="w-3 h-3 text-[var(--color-warning)] shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-[var(--color-text-primary)]">{c.key}:</strong> {c.ieee_format}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
