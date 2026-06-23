"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { formatTimestamp } from "@/lib/utils";
import type { AgentEvent } from "@/lib/types";
import { AGENT_CONFIG } from "@/lib/types";
import { Terminal, Filter } from "lucide-react";

const VIRTUAL_ITEM_HEIGHT = 28;
const VIRTUAL_OVERSCAN = 20;

interface ExecutionLogProps {
  events: AgentEvent[];
}

export function ExecutionLog({ events }: ExecutionLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);

  const filteredEvents = useMemo(() => {
    if (!filterAgent) return events;
    return events.filter((e) => e.agent === filterAgent);
  }, [events, filterAgent]);

  const uniqueAgents = useMemo(() => {
    return Array.from(new Set(events.map((e) => e.agent)));
  }, [events]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredEvents.length]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  const shouldVirtualize = filteredEvents.length > 200;

  const { visibleStart, visibleEnd } = useMemo(() => {
    if (!shouldVirtualize) return { visibleStart: 0, visibleEnd: filteredEvents.length };
    const start = Math.max(0, Math.floor(scrollTop / VIRTUAL_ITEM_HEIGHT) - VIRTUAL_OVERSCAN);
    const visible = Math.ceil(containerHeight / VIRTUAL_ITEM_HEIGHT);
    const end = Math.min(filteredEvents.length, start + visible + VIRTUAL_OVERSCAN * 2);
    return { visibleStart: start, visibleEnd: end };
  }, [shouldVirtualize, scrollTop, containerHeight, filteredEvents.length]);

  const visibleEvents = shouldVirtualize
    ? filteredEvents.slice(visibleStart, visibleEnd)
    : filteredEvents;

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-[var(--color-text-muted)] text-sm gap-2 p-4">
        <Terminal className="w-8 h-8 opacity-30" />
        <span>Execution logs will appear here</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)]/50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider font-sans">
            Execution Log
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            {filteredEvents.length} entries
          </span>
          {filterAgent && (
            <button
              onClick={() => setFilterAgent(null)}
              className="text-[10px] text-[var(--color-accent)] hover:underline flex items-center gap-1"
            >
              <Filter className="w-2.5 h-2.5" />
              Clear
            </button>
          )}
        </div>
        {shouldVirtualize && (
          <span className="text-[9px] bg-[var(--color-warning)]/15 text-[var(--color-warning)] px-1.5 py-0.5 rounded font-mono">
            VIRTUALIZED
          </span>
        )}
      </div>

      {/* Agent filter */}
      {uniqueAgents.length > 1 && (
        <div className="flex flex-wrap gap-1 px-4 py-1.5 border-b border-[var(--color-border)]/30">
          {uniqueAgents.map((agent) => {
            const config = AGENT_CONFIG[agent];
            return (
              <button
                key={agent}
                onClick={() => setFilterAgent(filterAgent === agent ? null : agent)}
                className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium transition-colors ${
                  filterAgent === agent
                    ? "bg-[var(--color-accent)]/20 text-[var(--color-accent)] border border-[var(--color-accent)]/30"
                    : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] border border-transparent"
                }`}
              >
                {config?.label || agent}
              </button>
            );
          })}
        </div>
      )}

      {/* Log entries */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-[11px]"
      >
        {shouldVirtualize && visibleStart > 0 && (
          <div style={{ height: visibleStart * VIRTUAL_ITEM_HEIGHT }} className="shrink-0" />
        )}

        {visibleEvents.map((e, i) => {
          const idx = shouldVirtualize ? visibleStart + i : i;
          return (
            <div
              key={idx}
              className="flex gap-2 py-0.5 px-4 text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)]/30"
            >
              <span className="text-[var(--color-text-muted)] opacity-50 shrink-0 w-16">
                {e.timestamp ? formatTimestamp(e.timestamp) : "--:--:--"}
              </span>
              <span
                className="shrink-0 w-20 truncate"
                style={{ color: AGENT_CONFIG[e.agent]?.color }}
              >
                [{AGENT_CONFIG[e.agent]?.label || e.agent}]
              </span>
              <span className="text-[var(--color-text-secondary)] truncate">
                {e.type}
                {e.data && Object.keys(e.data).length > 0 && (
                  <span className="text-[var(--color-text-muted)]">
                    {" "}
                    {JSON.stringify(e.data).slice(0, 120)}
                    {JSON.stringify(e.data).length > 120 ? "..." : ""}
                  </span>
                )}
              </span>
            </div>
          );
        })}

        {shouldVirtualize && visibleEnd < filteredEvents.length && (
          <div
            style={{ height: (filteredEvents.length - visibleEnd) * VIRTUAL_ITEM_HEIGHT }}
            className="shrink-0"
          />
        )}
      </div>
    </div>
  );
}
