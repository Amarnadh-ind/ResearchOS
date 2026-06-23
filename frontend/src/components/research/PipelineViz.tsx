"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AGENT_CONFIG } from "@/lib/types";
import type { PipelineAgent } from "@/lib/types";
import { Check, X, Loader2, Minus, Clock } from "lucide-react";
import { useResearchStore } from "@/stores/research-store";

interface PipelineVizProps {
  agents: PipelineAgent[];
}

function StatusIcon({ status }: { status: PipelineAgent["status"] }) {
  switch (status) {
    case "completed":
      return <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />;
    case "error":
      return <X className="w-3.5 h-3.5 text-[var(--color-error)]" />;
    case "running":
      return <Loader2 className="w-3.5 h-3.5 text-[var(--color-accent)] animate-spin" />;
    case "skipped":
      return <Minus className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />;
    default:
      return <Clock className="w-3.5 h-3.5 text-[var(--color-text-muted)] opacity-40" />;
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSec = seconds % 60;
  return `${minutes}m ${remainingSec}s`;
}

export function PipelineViz({ agents }: PipelineVizProps) {
  const completedCount = agents.filter((a) => a.status === "completed").length;
  const errorCount = agents.filter((a) => a.status === "error").length;
  const progress = (completedCount / agents.length) * 100;
  const agentTimings = useResearchStore((s) => s.agentTimings);
  const [now, setNow] = useState(() => Date.now());

  // Update the "now" time every second for running agents
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          Pipeline
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-[var(--color-accent)] font-bold">
            {Math.round(progress)}%
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {completedCount}/{agents.length}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-full mb-4 overflow-hidden">
        <motion.div
          className="h-full rounded-full relative overflow-hidden"
          style={{
            background: errorCount > 0
              ? "linear-gradient(90deg, var(--color-success), var(--color-warning))"
              : "linear-gradient(90deg, var(--color-accent), var(--color-agent-novelty))",
          }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          {agents.some((a) => a.status === "running") && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
          )}
        </motion.div>
      </div>

      {/* Agent steps */}
      <div className="flex flex-col gap-1">
        {agents.map((agent, idx) => {
          const config = AGENT_CONFIG[agent.agent];
          const isActive = agent.status === "running";
          const isDone = agent.status === "completed";
          const hasError = agent.status === "error";
          const timing = agentTimings[agent.agent];
          const duration = timing?.completed
            ? timing.completed - timing.started
            : timing?.started && isActive
            ? now - timing.started
            : null;

          return (
            <motion.div
              key={agent.agent}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`flex items-center gap-3 py-2 px-2.5 rounded-lg transition-all duration-200 ${
                isActive
                  ? "bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20 shadow-sm shadow-[var(--color-accent)]/5"
                  : hasError
                  ? "bg-[var(--color-error)]/5 border border-[var(--color-error)]/10"
                  : isDone
                  ? "bg-[var(--color-success)]/5 border border-transparent"
                  : "hover:bg-[var(--color-bg-hover)] border border-transparent"
              }`}
            >
              {/* Step number */}
              <span className={`text-[10px] font-mono w-4 text-right ${isDone ? "text-[var(--color-success)]" : hasError ? "text-[var(--color-error)]" : "text-[var(--color-text-muted)]"}`}>
                {idx + 1}
              </span>

              {/* Status icon */}
              <StatusIcon status={agent.status} />

              {/* Agent label + timing */}
              <div className="flex-1 flex items-center justify-between min-w-0">
                <span
                  className={`text-xs truncate ${
                    agent.status === "pending"
                      ? "text-[var(--color-text-muted)] opacity-50"
                      : "text-[var(--color-text-secondary)]"
                  }`}
                >
                  {config?.icon} {config?.label || agent.agent}
                </span>
                {duration !== null && (
                  <span className={`text-[9px] font-mono ml-2 shrink-0 ${isActive ? "text-[var(--color-accent)]" : isDone ? "text-[var(--color-success)]/70" : "text-[var(--color-text-muted)]"}`}>
                    {formatDuration(duration)}
                  </span>
                )}
              </div>

              {/* Active indicator */}
              {isActive && (
                <div className="flex items-center gap-1">
                  <div className="status-dot running" />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
