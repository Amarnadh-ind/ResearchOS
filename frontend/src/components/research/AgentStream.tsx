"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { AGENT_CONFIG } from "@/lib/types";
import type { AgentEvent } from "@/lib/types";
import { formatTimestamp, preview } from "@/lib/utils";
import { ChevronDown, ChevronRight, X, Activity } from "lucide-react";

const ACTIVITY_LIMIT = 300;
const VIRTUAL_THRESHOLD = 100;
const ROW_HEIGHT = 52;
const OVERSCAN = 8;

interface AgentStreamProps {
  events: AgentEvent[];
  currentAgent: string | null;
}

export function AgentStream({ events, currentAgent }: AgentStreamProps) {
  const filtered = useMemo(
    () => events.filter((e) => e.type !== "debug" && e.type !== "progress" && e.type !== "expanded"),
    [events]
  );

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [agentFilter, setAgentFilter] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerH, setContainerH] = useState(600);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [filtered.length]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const obs = new ResizeObserver((e) => setContainerH(e[0]?.contentRect.height ?? 600));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const toggle = useCallback((k: string) => setExpanded((p) => ({ ...p, [k]: !p[k] })), []);

  const agents = useMemo(() => Array.from(new Set(filtered.map((e) => e.agent))), [filtered]);
  const display = useMemo(
    () => (agentFilter ? filtered.filter((e) => e.agent === agentFilter) : filtered),
    [filtered, agentFilter]
  );

  const virtualize = display.length > VIRTUAL_THRESHOLD;
  const { start, end } = useMemo(() => {
    if (!virtualize) return { start: 0, end: display.length };
    const s = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    return { start: s, end: Math.min(display.length, s + Math.ceil(containerH / ROW_HEIGHT) + OVERSCAN * 2) };
  }, [virtualize, scrollTop, containerH, display.length]);

  const visible = virtualize ? display.slice(start, end) : display;

  if (events.length === 0 && !currentAgent) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--color-text-muted)]">
        <Activity className="w-10 h-10 opacity-15" />
        <div className="text-center">
          <div className="text-[12px] font-medium mb-1">Activity stream</div>
          <div className="text-[10px]">Events will appear here as agents work</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      onScroll={() => virtualize && setScrollTop(scrollRef.current?.scrollTop ?? 0)}
      className="h-full overflow-y-auto px-3 sm:px-4 py-3"
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
            Activity
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            {display.length}
          </span>
          {agentFilter && (
            <button
              onClick={() => setAgentFilter(null)}
              className="flex items-center gap-1 text-[10px] text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
            >
              <X className="w-2.5 h-2.5" />
              clear
            </button>
          )}
        </div>
        {virtualize && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--color-warning)]/10 text-[var(--color-warning)] font-mono">
            virtualized
          </span>
        )}
      </div>

      {/* Agent filters */}
      {agents.length > 1 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {agents.map((a) => {
            const c = AGENT_CONFIG[a];
            return (
              <button
                key={a}
                onClick={() => setAgentFilter(agentFilter === a ? null : a)}
                className={`text-[9px] sm:text-[10px] px-1.5 sm:px-2 py-0.5 rounded font-medium transition-colors ${
                  agentFilter === a
                    ? "bg-[var(--color-accent-subtle)] text-[var(--color-accent)] border border-[var(--color-border-accent)]"
                    : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] border border-transparent hover:border-[var(--color-border-active)]"
                }`}
              >
                {c?.icon} {c?.label || a}
              </button>
            );
          })}
        </div>
      )}

      {/* Virtual spacer top */}
      {virtualize && start > 0 && <div style={{ height: start * ROW_HEIGHT }} />}

      {/* Rows */}
      {visible.map((event, i) => {
        const idx = virtualize ? start + i : i;
        const key = `${event.agent}-${event.type}-${idx}`;
        const c = AGENT_CONFIG[event.agent] || { label: event.agent, color: "var(--color-text-muted)", icon: "\u2699" };
        const isOpen = expanded[key];
        const isError = event.type === "error";
        const isOk = event.type === "completed";
        const data = (event.data || {}) as Record<string, unknown>;
        const resp = (data.response_preview as string) || (data.response as string) || "";
        const latency = (data.latency as number) || (data.latency_ms as number) || 0;

        return (
          <div
            key={key}
            className={`activity-row group rounded-md mb-0.5 ${
              isError
                ? "bg-[var(--color-error)]/5"
                : isOk
                ? "bg-[var(--color-bg-secondary)]/30"
                : ""
            }`}
          >
            <div
              className="flex items-center gap-1.5 sm:gap-2 py-1.5 sm:py-2 px-2 sm:px-2.5 cursor-pointer select-none"
              onClick={() => resp && toggle(key)}
            >
              {/* Status indicator */}
              <div
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: isError ? "var(--color-error)" : isOk ? "var(--color-success)" : c.color }}
              />

              {/* Agent label */}
              <span className="text-[10px] sm:text-[11px] font-medium shrink-0" style={{ color: c.color }}>
                {c.label}
              </span>

              {/* Event type badge */}
              <span
                className={`text-[8px] sm:text-[9px] px-1 sm:px-1.5 py-0 rounded font-medium shrink-0 ${
                  isError
                    ? "bg-[var(--color-error)]/10 text-[var(--color-error)]"
                    : isOk
                    ? "bg-[var(--color-success)]/10 text-[var(--color-success)]"
                    : "bg-[var(--color-accent-subtle)] text-[var(--color-accent)]"
                }`}
              >
                {event.type}
              </span>

              {/* Preview */}
              {!isOpen && resp && (
                <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] truncate flex-1 font-mono">
                  {preview(resp, 100)}
                </span>
              )}

              {/* Latency */}
              {latency > 0 && (
                <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono shrink-0">
                  {latency >= 1000 ? `${(latency / 1000).toFixed(1)}s` : `${latency}ms`}
                </span>
              )}

              {/* Timestamp */}
              <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                {event.timestamp ? formatTimestamp(event.timestamp) : ""}
              </span>

              {/* Expand chevron */}
              {resp && (
                <span className="text-[var(--color-text-muted)] shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </span>
              )}
            </div>

            {/* Expanded content */}
            {isOpen && resp && (
              <div className="px-2.5 pb-2 pt-0.5 border-t border-[var(--color-border)]">
                <pre className="text-[9px] sm:text-[10px] text-[var(--color-text-secondary)] bg-[var(--color-bg-primary)] border border-[var(--color-border)] p-2 rounded font-mono whitespace-pre-wrap max-h-32 overflow-y-auto leading-relaxed">
                  {preview(resp, ACTIVITY_LIMIT)}
                </pre>
              </div>
            )}
          </div>
        );
      })}

      {/* Virtual spacer bottom */}
      {virtualize && end < display.length && (
        <div style={{ height: (display.length - end) * ROW_HEIGHT }} />
      )}

      {/* Running indicator */}
      {currentAgent && (
        <div className="flex items-center gap-2 py-2 px-2.5 mt-1">
          <div className="status-dot running" />
          <span className="text-[10px] sm:text-[11px] text-[var(--color-text-muted)]">
            <span style={{ color: AGENT_CONFIG[currentAgent]?.color }}>
              {AGENT_CONFIG[currentAgent]?.label || currentAgent}
            </span>
            {" "}working
          </span>
        </div>
      )}
    </div>
  );
}
