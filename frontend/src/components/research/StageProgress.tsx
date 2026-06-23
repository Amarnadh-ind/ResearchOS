"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  PIPELINE_STAGES,
  getStageStatus,
  getCurrentStageIndex,
} from "@/lib/types";
import type { PipelineAgent } from "@/lib/types";
import { Check, Loader2, Clock, Minus } from "lucide-react";

interface StageProgressProps {
  agents: PipelineAgent[];
  runtime?: number | null;
}

function formatRuntime(ms: number | null): string {
  if (ms === null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSec = seconds % 60;
  return `${minutes}m ${remainingSec}s`;
}

export function StageProgress({ agents, runtime }: StageProgressProps) {
  const stages = useMemo(() => {
    return PIPELINE_STAGES.map((stage) => ({
      ...stage,
      status: getStageStatus(stage, agents),
    }));
  }, [agents]);

  const currentIndex = useMemo(() => getCurrentStageIndex(agents), [agents]);

  const completedCount = stages.filter((s) => s.status === "completed").length;
  const activeCount = stages.filter((s) => s.status === "active").length;
  const progressPercent = Math.round((completedCount / stages.length) * 100);

  return (
    <div className="p-4">
      {/* Runtime + Progress */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          Progress
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-medium text-[var(--color-accent)]">
            {progressPercent}%
          </span>
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-[var(--color-text-muted)]" />
            <span className="text-xs font-mono text-[var(--color-text-secondary)]">
              {formatRuntime(runtime ?? null)}
            </span>
          </div>
        </div>
      </div>

      {/* Animated progress bar */}
      <div className="w-full h-1.5 bg-[var(--color-bg-tertiary)] rounded-full mb-4 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{
            background: activeCount > 0
              ? "linear-gradient(90deg, var(--color-success), var(--color-accent))"
              : "linear-gradient(90deg, var(--color-success), var(--color-success))",
          }}
          initial={{ width: 0 }}
          animate={{ width: `${progressPercent}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>

      {/* Stage progress bar */}
      <div className="stage-progress mb-4">
        {stages.map((stage) => (
          <div
            key={stage.key}
            className={`stage-segment ${
              stage.status === "completed"
                ? "completed"
                : stage.status === "active"
                ? "active"
                : ""
            }`}
          />
        ))}
      </div>

      {/* Stage list */}
      <div className="flex flex-col gap-0.5">
        {stages.map((stage, idx) => {
          const isActive = stage.status === "active";
          const isDone = stage.status === "completed";
          const hasError = stage.status === "error";
          const isFuture = stage.status === "pending" && idx > currentIndex;
          const isSkipped = idx >= stages.length - 2 && !isDone && !isActive;

          return (
            <motion.div
              key={stage.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03, duration: 0.2 }}
              className={`flex items-center gap-2.5 py-1.5 px-2 rounded-md transition-colors duration-150 ${
                isActive
                  ? "bg-[var(--color-accent)]/8"
                  : hasError
                  ? "bg-[var(--color-error)]/5"
                  : isDone
                  ? "bg-[var(--color-success)]/3"
                  : isFuture
                  ? "opacity-40"
                  : isSkipped
                  ? "opacity-30"
                  : "hover:bg-[var(--color-bg-hover)]"
              }`}
            >
              {/* Status icon */}
              {isDone ? (
                <Check className="w-3.5 h-3.5 text-[var(--color-success)] shrink-0" />
              ) : isActive ? (
                <Loader2 className="w-3.5 h-3.5 text-[var(--color-accent)] animate-spin shrink-0" />
              ) : hasError ? (
                <span className="w-3.5 h-3.5 flex items-center justify-center text-[var(--color-error)] text-xs shrink-0">
                  \u2715
                </span>
              ) : isSkipped ? (
                <Minus className="w-3.5 h-3.5 text-[var(--color-text-muted)] shrink-0" />
              ) : (
                <Clock className="w-3.5 h-3.5 text-[var(--color-text-muted)] opacity-30 shrink-0" />
              )}

              {/* Label */}
              <div className="flex-1 flex items-center gap-1.5 min-w-0">
                <span className="text-[11px]">{stage.icon}</span>
                <span
                  className={`text-[11px] font-medium ${
                    isDone
                      ? "text-[var(--color-success)]"
                      : isActive
                      ? "text-[var(--color-text-primary)]"
                      : hasError
                      ? "text-[var(--color-error)]"
                      : "text-[var(--color-text-muted)]"
                  }`}
                >
                  {stage.label}
                </span>
              </div>

              {/* Active pulse */}
              {isActive && (
                <div className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] animate-pulse" />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

export function StageProgressSkeleton() {
  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="skeleton skeleton-text w-16" />
        <div className="skeleton skeleton-text w-20" />
      </div>
      <div className="w-full h-1.5 bg-[var(--color-bg-tertiary)] rounded-full mb-4">
        <div className="skeleton h-full rounded-full w-1/3" />
      </div>
      <div className="stage-progress mb-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="stage-segment" />
        ))}
      </div>
      <div className="flex flex-col gap-1">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2.5 py-1.5 px-2">
            <div className="skeleton skeleton-circle w-3.5 h-3.5" />
            <div className="skeleton skeleton-text w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}
