"use client";

import { formatTimestamp } from "@/lib/utils";
import type { AgentEvent } from "@/lib/types";
import { AGENT_CONFIG } from "@/lib/types";
import { Terminal } from "lucide-react";

interface ExecutionLogProps {
  events: AgentEvent[];
}

export function ExecutionLog({ events }: ExecutionLogProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-[var(--color-text-muted)] text-sm gap-2 p-4">
        <Terminal className="w-8 h-8 opacity-30" />
        <span>Execution logs will appear here</span>
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full font-mono text-xs">
      <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-sans">
        Execution Log
      </div>
      {events.map((e, i) => (
        <div key={i} className="flex gap-2 py-0.5 text-[var(--color-text-muted)]">
          <span className="text-[var(--color-text-muted)] opacity-50 shrink-0">
            {e.timestamp ? formatTimestamp(e.timestamp) : "--:--:--"}
          </span>
          <span style={{ color: AGENT_CONFIG[e.agent]?.color }}>
            [{AGENT_CONFIG[e.agent]?.label || e.agent}]
          </span>
          <span className="text-[var(--color-text-secondary)]">
            {e.type} {JSON.stringify(e.data)}
          </span>
        </div>
      ))}
    </div>
  );
}
