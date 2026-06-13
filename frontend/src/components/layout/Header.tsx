"use client";

import { Cpu, Activity } from "lucide-react";

interface HeaderProps {
  isRunning: boolean;
  status: string | null;
  hasSession?: boolean;
  onNewSession?: () => void;
}

export function Header({ isRunning, status, hasSession = false, onNewSession }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--color-accent)]/15">
          <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
        </div>
        <div>
          <h1 className="text-sm font-bold gradient-text tracking-tight">ResearchOS</h1>
          <p className="text-[10px] text-[var(--color-text-muted)]">Autonomous Research Laboratory</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {hasSession && !isRunning && onNewSession && (
          <button
            onClick={onNewSession}
            className="text-xs px-2.5 py-1 rounded-md bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] font-semibold transition-colors cursor-pointer shadow-sm"
          >
            New Session
          </button>
        )}
        {isRunning && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20">
            <Activity className="w-3 h-3 text-[var(--color-accent)] animate-pulse" />
            <span className="text-xs text-[var(--color-accent)]">
              {status || "Processing"}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${isRunning ? "bg-[var(--color-accent)] animate-pulse" : "bg-[var(--color-success)]"}`} />
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {isRunning ? "Active" : "Ready"}
          </span>
        </div>
      </div>
    </header>
  );
}
