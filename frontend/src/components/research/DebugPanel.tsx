"use client";


import { useResearchStore } from "@/stores/research-store";
import { Terminal, Cpu, FileText, Globe, BookOpen, Key, X } from "lucide-react";
import { AGENT_CONFIG } from "@/lib/types";

export function DebugPanel({ onClose }: { onClose?: () => void }) {
  const { currentAgent, events, sources: rawSources, citations: rawCitations, prompt } = useResearchStore();
  const sources = Array.isArray(rawSources) ? rawSources : [];
  const citations = Array.isArray(rawCitations) ? rawCitations : [];

  const debugEvents = events.filter(e => e.type === "debug");
  const latestDebug = debugEvents.length > 0 ? debugEvents[debugEvents.length - 1] : null;

  const activeAgentConfig = currentAgent ? AGENT_CONFIG[currentAgent] : null;

  const debugData = latestDebug?.data as Record<string, unknown> | undefined;
  const currentTopic = (debugData?.topic as string) || prompt || "Autonomous Multi-Agent Systems";
  const currentPrompt = (debugData?.prompt as string) || "";
  const currentResponse = (debugData?.response as string) || "";

  return (
    <div className="h-full flex flex-col w-full bg-[var(--color-bg-secondary)]">
      {/* Header */}
      <div className="p-3 sm:p-4 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--color-accent)]" />
          <h3 className="text-[11px] sm:text-sm font-bold text-[var(--color-text-primary)]">Debug</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] sm:text-[10px] bg-[var(--color-accent)]/15 text-[var(--color-accent)] px-1.5 sm:px-2 py-0.5 rounded font-mono font-bold">
            LIVE
          </span>
          {onClose && (
            <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 flex flex-col gap-3 sm:gap-4 text-xs">
        {/* Current Topic */}
        <DebugSection label="Current Topic" icon={<Cpu className="w-3 h-3 text-[var(--color-accent)]" />}>
          <span className="font-semibold text-[var(--color-text-primary)] text-[11px] sm:text-xs">{currentTopic}</span>
        </DebugSection>

        {/* Current Agent */}
        <DebugSection label="Current Agent">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-[var(--color-text-primary)] capitalize text-[11px] sm:text-xs">
              {currentAgent ? currentAgent.replace("_", " ") : "Idle"}
            </span>
            {activeAgentConfig && (
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center text-sm sm:text-base"
                style={{ backgroundColor: `${activeAgentConfig.color}20`, border: `1px solid ${activeAgentConfig.color}40` }}
              >
                {activeAgentConfig.icon}
              </div>
            )}
          </div>
        </DebugSection>

        {/* Current Prompt */}
        <DebugSection label="Current Prompt" icon={<Cpu className="w-3 h-3 text-[var(--color-accent)]" />}>
          <div className="h-24 sm:h-32 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg font-mono text-[9px] sm:text-[10px] text-[var(--color-text-secondary)] whitespace-pre-wrap">
            {currentPrompt || "No prompt payload in current agent step."}
          </div>
        </DebugSection>

        {/* Current LLM Response */}
        <DebugSection label="Current LLM Response" icon={<FileText className="w-3 h-3 text-[var(--color-success)]" />}>
          <div className="h-32 sm:h-44 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg font-mono text-[9px] sm:text-[10px] text-[var(--color-text-primary)] whitespace-pre-wrap">
            {currentResponse || "Waiting for active LLM generation response..."}
          </div>
        </DebugSection>

        {/* Current Sources */}
        <DebugSection label="Current Sources" icon={<Globe className="w-3 h-3 text-[var(--color-info)]" />} count={sources.length}>
          <div className="max-h-24 sm:max-h-28 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg flex flex-col gap-1.5">
            {sources.length === 0 ? (
              <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] italic">No sources collected yet.</span>
            ) : (
              sources.map((s, idx) => (
                <div key={idx} className="flex flex-col pb-1.5 border-b border-[var(--color-border)] last:border-b-0">
                  <span className="font-semibold text-[9px] sm:text-[10px] text-[var(--color-text-primary)] truncate">{s.title || "Untitled Source"}</span>
                  <a href={s.url} target="_blank" rel="noreferrer" className="text-[8px] sm:text-[9px] text-[var(--color-accent)] truncate hover:underline">
                    {s.url}
                  </a>
                </div>
              ))
            )}
          </div>
        </DebugSection>

        {/* Current Citations */}
        <DebugSection label="Current Citations" icon={<BookOpen className="w-3 h-3 text-[var(--color-warning)]" />} count={citations.length}>
          <div className="max-h-24 sm:max-h-28 overflow-y-auto p-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg flex flex-col gap-1">
            {citations.length === 0 ? (
              <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] italic">No citations verified yet.</span>
            ) : (
              citations.map((c, idx) => (
                <div key={idx} className="flex items-start gap-1 text-[9px] sm:text-[10px] text-[var(--color-text-secondary)]">
                  <Key className="w-3 h-3 text-[var(--color-warning)] shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-[var(--color-text-primary)]">{c.key}:</strong> {c.ieee_format}
                  </span>
                </div>
              ))
            )}
          </div>
        </DebugSection>
      </div>
    </div>
  );
}

function DebugSection({
  label,
  icon,
  count,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[9px] sm:text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider flex items-center gap-1">
        {icon}
        {label}
        {count !== undefined && (
          <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-normal">({count})</span>
        )}
      </span>
      {children}
    </div>
  );
}
