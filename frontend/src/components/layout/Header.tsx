"use client";

import { Pen } from "lucide-react";
import { ModelHealthBadges } from "@/components/research/ModelHealthBadges";

interface HeaderProps {
  isRunning: boolean;
  status: string | null;
  hasSession?: boolean;
  onNewSession?: () => void;
  onLoadDemo?: () => void;
}

export function Header({ isRunning, status, hasSession = false, onNewSession, onLoadDemo }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-3 sm:px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/60 z-20">
      <div className="flex items-center gap-2 sm:gap-2.5">
        <div className="flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-[var(--color-accent-subtle)]">
          <Pen className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-[var(--color-accent)]" />
        </div>
        <span className="text-[12px] sm:text-[13px] font-semibold text-[var(--color-text-primary)] tracking-tight">
          ResearchOS
        </span>
        <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] font-mono hidden sm:inline">
          v0.2
        </span>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2">
        {!hasSession && onLoadDemo && (
          <button
            onClick={onLoadDemo}
            className="text-[10px] sm:text-[11px] px-2 sm:px-2.5 py-1 rounded-md bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)] font-medium transition-colors"
          >
            Demo
          </button>
        )}
        {hasSession && onNewSession && (
          <button
            onClick={onNewSession}
            className="text-[10px] sm:text-[11px] px-2 sm:px-2.5 py-1 rounded-md bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)] font-medium transition-colors"
          >
            New
          </button>
        )}

        <ModelHealthBadges />

        <div className="flex items-center gap-1.5 px-1.5 sm:px-2 py-1 rounded-md bg-[var(--color-bg-tertiary)]">
          <div className={`status-dot ${isRunning ? "running" : "completed"}`} />
          <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] font-mono">
            {isRunning ? (status || "active") : "ready"}
          </span>
        </div>
      </div>
    </header>
  );
}
