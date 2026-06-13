"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Globe,
  FileText,
  BookOpen,
  Terminal,
  Zap,
  Braces,
  Network,
  Cpu,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PromptInput } from "@/components/research/PromptInput";
import { AgentStream } from "@/components/research/AgentStream";
import { PipelineViz } from "@/components/research/PipelineViz";
import { SourcesPanel } from "@/components/research/SourcesPanel";
import { PaperViewer } from "@/components/research/PaperViewer";
import { CitationPanel } from "@/components/research/CitationPanel";
import { ClaimGraph } from "@/components/research/ClaimGraph";
import { ExecutionLog } from "@/components/research/ExecutionLog";
import { DiagnosticsTab } from "@/components/research/DiagnosticsTab";
import { DebugPanel } from "@/components/research/DebugPanel";
import { useResearch } from "@/hooks/useResearch";

type PanelKey = "stream" | "sources" | "graph" | "paper" | "citations" | "logs" | "diagnostics";

const TABS: { key: PanelKey; label: string; icon: typeof Activity }[] = [
  { key: "stream", label: "Activity", icon: Activity },
  { key: "sources", label: "Sources", icon: Globe },
  { key: "graph", label: "Graph", icon: Network },
  { key: "paper", label: "Paper", icon: FileText },
  { key: "citations", label: "Citations", icon: BookOpen },
  { key: "logs", label: "Logs", icon: Terminal },
  { key: "diagnostics", label: "Diagnostics", icon: Cpu },
];

export default function HomePage() {
  const research = useResearch();

  const hasSession = research.sessionId !== null;

  return (
    <div className="flex flex-col h-screen bg-[var(--color-bg-primary)]">
      <Header
        isRunning={research.isRunning}
        status={research.status}
        hasSession={hasSession}
        onNewSession={research.reset}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* ── Landing / Hero ─────────────────────────── */}
        {!hasSession && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 flex flex-col items-center justify-center px-6 gap-8"
          >
            <div className="text-center">
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.6 }}
                className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--color-accent)]/15 mb-4 glow-pulse"
              >
                <Braces className="w-8 h-8 text-[var(--color-accent)]" />
              </motion.div>
              <h2 className="text-3xl font-bold gradient-text mb-2">
                ResearchOS
              </h2>
              <p className="text-sm text-[var(--color-text-muted)] max-w-md mx-auto">
                Autonomous multi-agent research laboratory. Enter a research
                question and watch 10 specialized AI agents produce an
                IEEE-grade paper with verified citations.
              </p>
            </div>

            <PromptInput
              onSubmit={research.startResearch}
              isRunning={research.isRunning}
            />

            <div className="flex gap-4 flex-wrap justify-center max-w-2xl">
              {[
                {
                  icon: Zap,
                  label: "10 Specialized Agents",
                  desc: "Planner → IEEE Formatter",
                },
                {
                  icon: Globe,
                  label: "Web Research",
                  desc: "Search, browse, extract",
                },
                {
                  icon: BookOpen,
                  label: "Citation Integrity",
                  desc: "Verified IEEE citations",
                },
                {
                  icon: FileText,
                  label: "Paper Generation",
                  desc: "Academic-grade output",
                },
              ].map((f, i) => (
                <motion.div
                  key={f.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className="glass-card px-4 py-3 flex items-center gap-3 min-w-[200px]"
                >
                  <f.icon className="w-4 h-4 text-[var(--color-accent)]" />
                  <div>
                    <div className="text-xs font-medium text-[var(--color-text-primary)]">
                      {f.label}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-muted)]">
                      {f.desc}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── Research Workspace ──────────────────────── */}
        {hasSession && (
          <div className="flex-1 flex overflow-hidden">
            {/* Left sidebar: Pipeline */}
            <div className="w-56 border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)]/30 overflow-y-auto shrink-0">
              <PipelineViz agents={research.agents} />
            </div>

            {/* Center: tabbed content */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Prompt bar */}
              <div className="px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/20">
                <PromptInput
                  onSubmit={research.startResearch}
                  isRunning={research.isRunning}
                />
              </div>

              {/* Tab bar */}
              <div className="flex items-center gap-1 px-4 py-1.5 border-b border-[var(--color-border)]">
                {TABS.map((tab) => (
                  <button
                    key={tab.key}
                    id={`tab-${tab.key}`}
                    onClick={() => research.setActivePanel(tab.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors ${
                      research.activePanel === tab.key
                        ? "bg-[var(--color-accent)]/15 text-[var(--color-accent)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]"
                    }`}
                  >
                    <tab.icon className="w-3.5 h-3.5" />
                    {tab.label}
                  </button>
                ))}

                {/* Connection indicator */}
                <div className="ml-auto flex items-center gap-1.5">
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      research.isConnected
                        ? "bg-[var(--color-success)]"
                        : "bg-[var(--color-error)]"
                    }`}
                  />
                  <span className="text-[10px] text-[var(--color-text-muted)]">
                    {research.isConnected ? "Live" : "Offline"}
                  </span>
                </div>
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="wait">
                  {research.activePanel === "stream" && (
                    <motion.div
                      key="stream"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <AgentStream
                        events={research.events}
                        currentAgent={research.currentAgent}
                      />
                    </motion.div>
                  )}
                  {research.activePanel === "sources" && (
                    <motion.div
                      key="sources"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <SourcesPanel sources={research.sources} />
                    </motion.div>
                  )}
                  {research.activePanel === "graph" && (
                    <motion.div
                      key="graph"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <ClaimGraph events={research.events} />
                    </motion.div>
                  )}
                  {research.activePanel === "paper" && (
                    <motion.div
                      key="paper"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <PaperViewer
                        markdown={research.markdown}
                        title={research.paper?.title || "paper"}
                        paper={research.paper}
                      />
                    </motion.div>
                  )}
                  {research.activePanel === "citations" && (
                    <motion.div
                      key="citations"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <CitationPanel citations={research.citations} />
                    </motion.div>
                  )}
                  {research.activePanel === "logs" && (
                    <motion.div
                      key="logs"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <ExecutionLog events={research.events} />
                    </motion.div>
                  )}
                  {research.activePanel === "diagnostics" && (
                    <motion.div
                      key="diagnostics"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <DiagnosticsTab />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Right sidebar: Live Debug Panel */}
            <DebugPanel />
          </div>
        )}
      </main>

      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-1 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]/30 text-[10px] text-[var(--color-text-muted)]">
        <span>ResearchOS v0.1.0</span>
        <div className="flex items-center gap-4">
          {research.sessionId && (
            <span>Session: {research.sessionId.slice(0, 8)}...</span>
          )}
          {research.claims > 0 && <span>Claims: {research.claims}</span>}
          {research.sources.length > 0 && (
            <span>Sources: {research.sources.length}</span>
          )}
          <span>Agents: 10</span>
        </div>
      </div>
    </div>
  );
}
