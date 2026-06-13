"use client";

import { motion } from "framer-motion";
import { AGENT_CONFIG } from "@/lib/types";
import type { PipelineAgent } from "@/lib/types";
import { Check, X, Loader2, Minus, Clock } from "lucide-react";

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

export function PipelineViz({ agents }: PipelineVizProps) {
  const completedCount = agents.filter((a) => a.status === "completed").length;
  const progress = (completedCount / agents.length) * 100;

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          Pipeline
        </h3>
        <span className="text-xs text-[var(--color-text-muted)]">
          {completedCount}/{agents.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-[var(--color-bg-tertiary)] rounded-full mb-4 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{
            background: "linear-gradient(90deg, var(--color-accent), var(--color-agent-novelty))",
          }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* Agent steps */}
      <div className="flex flex-col gap-1">
        {agents.map((agent, idx) => {
          const config = AGENT_CONFIG[agent.agent];
          const isActive = agent.status === "running";

          return (
            <motion.div
              key={agent.agent}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`flex items-center gap-3 py-1.5 px-2 rounded-md transition-colors duration-200 ${
                isActive
                  ? "bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20"
                  : "hover:bg-[var(--color-bg-hover)]"
              }`}
            >
              {/* Step number */}
              <span className="text-[10px] font-mono text-[var(--color-text-muted)] w-4 text-right">
                {idx + 1}
              </span>

              {/* Status icon */}
              <StatusIcon status={agent.status} />

              {/* Agent label */}
              <span
                className={`text-xs flex-1 ${
                  agent.status === "pending"
                    ? "text-[var(--color-text-muted)] opacity-50"
                    : "text-[var(--color-text-secondary)]"
                }`}
              >
                {config?.icon} {config?.label || agent.agent}
              </span>

              {/* Active glow */}
              {isActive && (
                <div className="status-dot running" />
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
