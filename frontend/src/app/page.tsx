"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Globe,
  FileText,
  BookOpen,
  Terminal,
  Cpu,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Wifi,
  WifiOff,
  Search,
  Pen,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  X,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { loadDemoData } from "@/lib/demo-data";
import { PromptInput } from "@/components/research/PromptInput";
import { AgentStream } from "@/components/research/AgentStream";
import { StageProgress } from "@/components/research/StageProgress";
import { SourcesPanel } from "@/components/research/SourcesPanel";
import { PaperViewer } from "@/components/research/PaperViewer";
import { CitationPanel } from "@/components/research/CitationPanel";
import { ClaimGraph } from "@/components/research/ClaimGraph";
import { ExecutionLog } from "@/components/research/ExecutionLog";
import { DiagnosticsTab } from "@/components/research/DiagnosticsTab";
import { DebugPanel } from "@/components/research/DebugPanel";
import { TokenCounter } from "@/components/research/TokenCounter";
import { useResearch } from "@/hooks/useResearch";

type PanelKey = "stream" | "sources" | "graph" | "paper" | "citations" | "logs" | "diagnostics";

const TABS: { key: PanelKey; label: string; icon: typeof Activity }[] = [
  { key: "stream", label: "Activity", icon: Activity },
  { key: "sources", label: "Sources", icon: Globe },
  { key: "graph", label: "Graph", icon: Search },
  { key: "paper", label: "Paper", icon: FileText },
  { key: "citations", label: "Citations", icon: BookOpen },
  { key: "logs", label: "Logs", icon: Terminal },
  { key: "diagnostics", label: "Diagnostics", icon: Cpu },
];

function formatRuntime(ms: number | null): string {
  if (ms === null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSec = seconds % 60;
  return `${minutes}m ${remainingSec}s`;
}

const panelVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export default function HomePage() {
  const research = useResearch();
  const hasSession = research.sessionId !== null;
  const isComplete = research.status === "completed";
  const isFailed = research.status === "failed";
  const startedAt = research.startedAt;
  const completedAt = research.completedAt;
  const [now, setNow] = useState(() => Date.now());
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);

  useEffect(() => {
    if (!startedAt || completedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt, completedAt]);

  const runtime = completedAt && startedAt
    ? completedAt - startedAt
    : startedAt
    ? now - startedAt
    : null;

  const handleTabChange = useCallback((key: PanelKey) => {
    research.setActivePanel(key);
    setMobileMenuOpen(false);
  }, [research]);

  return (
    <div className="flex flex-col h-[100dvh] bg-[var(--color-bg-primary)]">
      <div className="grid-bg" />

      <Header
        isRunning={research.isRunning}
        status={research.status}
        hasSession={hasSession}
        onNewSession={research.reset}
        onLoadDemo={loadDemoData}
      />

      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* ── Landing ──────────────────────────────────── */}
        {!hasSession && (
          <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 gap-6">
            <div className="text-center max-w-md">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--color-accent-subtle)] mb-4">
                <Pen className="w-6 h-6 text-[var(--color-accent)]" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-semibold text-[var(--color-text-primary)] mb-2 tracking-tight">
                ResearchOS
              </h1>
              <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                Multi-agent research pipeline. 10 specialized agents
                produce IEEE-grade papers with verified citations.
              </p>
            </div>

            <div className="w-full max-w-xl">
              <PromptInput
                onSubmit={research.startResearch}
                isRunning={research.isRunning}
              />
            </div>

            <div className="flex gap-2 sm:gap-3 flex-wrap justify-center">
              {[
                { icon: Activity, label: "10 Agents" },
                { icon: Globe, label: "Web Search" },
                { icon: BookOpen, label: "Citations" },
                { icon: FileText, label: "IEEE Paper" },
                { icon: Cpu, label: "Diagnostics" },
              ].map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-md bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-[10px] sm:text-[11px] text-[var(--color-text-muted)]"
                >
                  <f.icon className="w-3 h-3" />
                  {f.label}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Workspace ────────────────────────────────── */}
        {hasSession && (
          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar - desktop */}
            <div
              className={`hidden md:flex border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)]/40 overflow-y-auto shrink-0 flex-col transition-all duration-200 ${
                sidebarOpen ? "w-56" : "w-0 border-r-0"
              }`}
            >
              <div className="p-3 border-b border-[var(--color-border)]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
                    {isComplete && (
                      <span className="flex items-center gap-1 text-[var(--color-success)]">
                        <CheckCircle2 className="w-3 h-3" />
                        Complete
                      </span>
                    )}
                    {isFailed && (
                      <span className="flex items-center gap-1 text-[var(--color-error)]">
                        <AlertTriangle className="w-3 h-3" />
                        Failed
                      </span>
                    )}
                    {research.isRunning && !isComplete && !isFailed && (
                      <span className="flex items-center gap-1 text-[var(--color-accent)]">
                        <div className="status-dot running" />
                        Running
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                    className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors p-0.5"
                  >
                    {sidebarOpen ? <PanelLeftClose className="w-3 h-3" /> : <PanelLeftOpen className="w-3 h-3" />}
                  </button>
                </div>
              </div>
              <StageProgress agents={research.agents} runtime={runtime} />

              {research.stuckDetected && (
                <div className="p-3 mx-3 mb-3 rounded-lg bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/20">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-3 h-3 text-[var(--color-warning)]" />
                    <span className="text-[11px] font-medium text-[var(--color-warning)]">Stuck</span>
                  </div>
                  <button
                    onClick={research.recoverStuckSession}
                    className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-medium rounded bg-[var(--color-warning)]/20 hover:bg-[var(--color-warning)]/30 text-[var(--color-warning)] transition-colors mt-1"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Reconnect
                  </button>
                </div>
              )}
            </div>

            {/* Mobile sidebar overlay */}
            <AnimatePresence>
              {mobileMenuOpen && (
                <>
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="fixed inset-0 bg-black/50 z-40 md:hidden"
                    onClick={() => setMobileMenuOpen(false)}
                  />
                  <motion.div
                    initial={{ x: -280 }}
                    animate={{ x: 0 }}
                    exit={{ x: -280 }}
                    transition={{ type: "spring", damping: 25, stiffness: 300 }}
                    className="fixed left-0 top-0 bottom-0 w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] z-50 md:hidden flex flex-col overflow-y-auto"
                  >
                    <div className="p-3 border-b border-[var(--color-border)] flex items-center justify-between">
                      <span className="text-[11px] font-medium text-[var(--color-text-muted)]">Navigation</span>
                      <button onClick={() => setMobileMenuOpen(false)} className="text-[var(--color-text-muted)]">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="p-3 border-b border-[var(--color-border)]">
                      <div className="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
                        {isComplete && (
                          <span className="flex items-center gap-1 text-[var(--color-success)]">
                            <CheckCircle2 className="w-3 h-3" /> Complete
                          </span>
                        )}
                        {isFailed && (
                          <span className="flex items-center gap-1 text-[var(--color-error)]">
                            <AlertTriangle className="w-3 h-3" /> Failed
                          </span>
                        )}
                        {research.isRunning && !isComplete && !isFailed && (
                          <span className="flex items-center gap-1 text-[var(--color-accent)]">
                            <div className="status-dot running" /> Running
                          </span>
                        )}
                      </div>
                    </div>
                    <StageProgress agents={research.agents} runtime={runtime} />
                    {research.stuckDetected && (
                      <div className="p-3 mx-3 mb-3 rounded-lg bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/20">
                        <div className="flex items-center gap-2 mb-1">
                          <AlertTriangle className="w-3 h-3 text-[var(--color-warning)]" />
                          <span className="text-[11px] font-medium text-[var(--color-warning)]">Stuck</span>
                        </div>
                        <button
                          onClick={() => { research.recoverStuckSession(); setMobileMenuOpen(false); }}
                          className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-medium rounded bg-[var(--color-warning)]/20 hover:bg-[var(--color-warning)]/30 text-[var(--color-warning)] transition-colors mt-1"
                        >
                          <RefreshCw className="w-3 h-3" /> Reconnect
                        </button>
                      </div>
                    )}
                  </motion.div>
                </>
              )}
            </AnimatePresence>

            {/* Center */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Prompt bar */}
              <div className="px-3 sm:px-4 py-2 sm:py-2.5 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/30 flex items-center gap-2">
                <button
                  onClick={() => setMobileMenuOpen(true)}
                  className="md:hidden text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] p-1"
                >
                  <Menu className="w-4 h-4" />
                </button>
                <div className="flex-1">
                  <PromptInput
                    onSubmit={research.startResearch}
                    isRunning={research.isRunning}
                  />
                </div>
              </div>

              {/* Tabs - scrollable on mobile */}
              <div className="flex items-center gap-0.5 px-2 sm:px-3 py-1.5 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/20 overflow-x-auto scrollbar-none">
                {TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => handleTabChange(tab.key)}
                    className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 rounded text-[10px] sm:text-[11px] font-medium transition-colors duration-150 whitespace-nowrap shrink-0 ${
                      research.activePanel === tab.key
                        ? "bg-[var(--color-accent-subtle)] text-[var(--color-accent)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]"
                    }`}
                  >
                    <tab.icon className="w-3 h-3" />
                    <span className="hidden sm:inline">{tab.label}</span>
                  </button>
                ))}

                <div className="ml-auto flex items-center gap-1.5 px-2 py-1 rounded text-[10px] text-[var(--color-text-muted)] shrink-0">
                  {research.isConnected ? (
                    <Wifi className="w-3 h-3 text-[var(--color-success)]" />
                  ) : (
                    <WifiOff className="w-3 h-3 text-[var(--color-error)]" />
                  )}
                  <span className="font-mono hidden sm:inline">
                    {research.reconnecting ? "reconnecting" : research.isConnected ? "live" : "offline"}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="popLayout">
                  <motion.div
                    key={research.activePanel}
                    variants={panelVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.1 }}
                    className="h-full"
                  >
                    {research.activePanel === "stream" && (
                      <AgentStream events={research.events} currentAgent={research.currentAgent} />
                    )}
                    {research.activePanel === "sources" && (
                      <SourcesPanel sources={research.sources} />
                    )}
                    {research.activePanel === "graph" && (
                      <ClaimGraph events={research.events} />
                    )}
                    {research.activePanel === "paper" && (
                      <PaperViewer
                        markdown={research.isStreaming ? research.streamingContent : research.markdown}
                        title={research.paper?.title || "paper"}
                        paper={research.paper}
                        isStreaming={research.isStreaming}
                        sessionId={research.sessionId}
                      />
                    )}
                    {research.activePanel === "citations" && (
                      <CitationPanel citations={research.citations} />
                    )}
                    {research.activePanel === "logs" && (
                      <ExecutionLog events={research.events} />
                    )}
                    {research.activePanel === "diagnostics" && (
                      <DiagnosticsTab />
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>

            {/* Right sidebar - desktop only, collapsible */}
            <div className={`hidden lg:flex border-l border-[var(--color-border)] bg-[var(--color-bg-secondary)]/40 overflow-y-auto shrink-0 transition-all duration-200 ${
              debugOpen ? "w-80" : "w-0 border-l-0"
            }`}>
              {debugOpen && <DebugPanel />}
            </div>

            {/* Debug toggle - desktop */}
            {hasSession && !debugOpen && (
              <button
                onClick={() => setDebugOpen(true)}
                className="hidden lg:flex fixed right-0 top-1/2 -translate-y-1/2 z-40 w-6 h-24 rounded-l-lg bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-hover)] border-l border-y border-[var(--color-border)] items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
              >
                <Terminal className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* ── Completion Toast ─────────────────────────── */}
        <AnimatePresence>
          {isComplete && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="absolute bottom-16 left-1/2 -translate-x-1/2 z-40"
            >
              <div className="glass-panel px-4 sm:px-5 py-3 flex flex-col sm:flex-row items-center gap-3 sm:gap-5 shadow-2xl">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
                  <div>
                    <div className="text-xs font-semibold text-[var(--color-text-primary)]">Research Complete</div>
                    <div className="text-[10px] text-[var(--color-text-muted)]">
                      {research.agents.filter(a => a.status === "completed").length} agents
                      {runtime && ` \u00b7 ${formatRuntime(runtime)}`}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-[11px]">
                  <div className="text-center">
                    <div className="font-semibold text-[var(--color-text-primary)]">{research.sources.length}</div>
                    <div className="text-[9px] text-[var(--color-text-muted)]">Sources</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold text-[var(--color-text-primary)]">{research.claims}</div>
                    <div className="text-[9px] text-[var(--color-text-muted)]">Claims</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold text-[var(--color-text-primary)]">{research.citations.length}</div>
                    <div className="text-[9px] text-[var(--color-text-muted)]">Citations</div>
                  </div>
                </div>

                <button
                  onClick={() => research.setActivePanel("paper")}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--color-accent)] text-white text-[11px] font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
                >
                  <FileText className="w-3 h-3" />
                  View Paper
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Status bar */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-1.5 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]/60 text-[10px] text-[var(--color-text-muted)] z-20">
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="font-medium">ResearchOS</span>
          {research.sessionId && (
            <span className="font-mono text-[var(--color-text-muted)]">
              {research.sessionId.slice(0, 8)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 sm:gap-4">
          <TokenCounter />
          {runtime !== null && (
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3" />
              {formatRuntime(runtime)}
            </span>
          )}
          {research.claims > 0 && (
            <span className="font-mono hidden sm:inline">Claims: {research.claims}</span>
          )}
          {research.sources.length > 0 && (
            <span className="font-mono hidden sm:inline">Sources: {research.sources.length}</span>
          )}
        </div>
      </div>
    </div>
  );
}
