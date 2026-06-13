"use client";

import { useEffect, useState, useCallback } from "react";
import { useResearchStore } from "@/stores/research-store";
import { 
  Activity, RefreshCw, Cpu, Zap, DollarSign, Clock, 
  Database, ShieldAlert, Eye
} from "lucide-react";

interface CollapsibleJsonCardProps {
  title: string;
  data: any;
  defaultExpanded?: boolean;
}

function CollapsibleJsonCard({ title, data, defaultExpanded = false }: CollapsibleJsonCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  
  if (!data) {
    return (
      <div className="p-3 bg-[var(--color-bg-secondary)]/30 border border-[var(--color-border)] rounded text-[10px] text-[var(--color-text-muted)] italic font-mono">
        No data logged yet.
      </div>
    );
  }
  
  const jsonString = typeof data === "object" ? JSON.stringify(data, null, 2) : String(data);
  const lines = jsonString.split("\n");
  const sizeKb = (jsonString.length / 1024).toFixed(2);
  const isLong = lines.length > 4 || jsonString.length > 250;
  
  const shouldCollapse = isLong;
  const showContent = !shouldCollapse || expanded;
  
  return (
    <div className="border border-[var(--color-border)] rounded bg-[var(--color-bg-secondary)]/30 overflow-hidden flex flex-col w-full text-[10px]">
      <div 
        onClick={() => shouldCollapse && setExpanded(!expanded)}
        className={`flex items-center justify-between px-2.5 py-1 bg-[var(--color-bg-tertiary)]/70 text-[9px] font-bold uppercase tracking-wider select-none ${shouldCollapse ? "cursor-pointer hover:bg-[var(--color-bg-hover)]" : ""}`}
      >
        <div className="flex items-center gap-1.5 font-sans">
          <span className="text-[var(--color-text-secondary)]">{title}</span>
          <span className="text-[var(--color-text-muted)] font-mono normal-case">({sizeKb} KB, {lines.length} lines)</span>
        </div>
        {shouldCollapse && (
          <span className="text-[var(--color-accent)] hover:underline font-normal font-sans tracking-normal capitalize text-[9px]">
            {expanded ? "collapse" : "expand"}
          </span>
        )}
      </div>
      {showContent && (
        <pre className="p-2.5 text-[10px] font-mono text-[var(--color-text-secondary)] bg-[var(--color-bg-primary)]/80 border-t border-[var(--color-border)] overflow-x-auto whitespace-pre-wrap max-h-56">
          {jsonString}
        </pre>
      )}
    </div>
  );
}

interface Execution {
  id?: string;
  agent_name: string;
  status: string;
  input_data: unknown;
  output_data: unknown;
  tokens_used: number;
  duration_ms: number;
  error?: string;
  created_at: string;
  model_name?: string;
  tokens_in?: number;
  tokens_out?: number;
  cost?: number;
  latency?: number;
}

interface DiagnosticsData {
  session_id: string;
  topic: string;
  search_queries: string[];
  search_results: unknown[];
  browser_urls: string[];
  reader_documents: unknown[];
  claims_generated: unknown[];
  citations_collected: unknown[];
  writer_prompt: string;
  raw_llm_output: string;
  final_paper: unknown;
  citation_agent_input?: unknown;
  citation_agent_output?: unknown;
  citation_agent_error?: string;
  executions: Execution[];
}
export function DiagnosticsTab() {
  const { sessionId, isRunning } = useResearchStore();
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [providersHealth, setProvidersHealth] = useState<Record<string, {
    status: string;
    connected: boolean;
    latency: number;
    last_status: number;
    last_error: string;
    model_name: string;
    display_name: string;
    provider: string;
  }> | null>(null);

  const fetchDiagnostics = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/research/${sessionId}/diagnostics`);
      if (!res.ok) throw new Error("Failed to fetch diagnostics");
      const d = await res.json();
      setData(d as DiagnosticsData);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const fetchProvidersHealth = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/diagnostics/providers/details");
      if (!res.ok) throw new Error("Failed to fetch provider diagnostics");
      const d = await res.json();
      setProvidersHealth(d);
    } catch (err) {
      console.error("Error fetching provider diagnostics:", err);
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      const timer = setTimeout(() => {
        fetchDiagnostics();
        fetchProvidersHealth();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [sessionId, fetchDiagnostics, fetchProvidersHealth]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRunning && sessionId) {
      interval = setInterval(() => {
        fetchDiagnostics();
        fetchProvidersHealth();
      }, 4000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, sessionId, fetchDiagnostics, fetchProvidersHealth]);

  if (!sessionId) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-[var(--color-text-muted)]">
        <Activity className="w-12 h-12 mb-4 animate-pulse" />
        <p className="text-sm">No active research session to observe.</p>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-[var(--color-text-muted)]">
        <RefreshCw className="w-8 h-8 mb-4 animate-spin text-[var(--color-accent)]" />
        <p className="text-sm">Loading observability metrics...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-[var(--color-error)]">
        <ShieldAlert className="w-12 h-12 mb-4" />
        <p className="text-sm mb-2">Error connecting to diagnostics backend</p>
        <p className="text-xs text-[var(--color-text-muted)]">{error}</p>
      </div>
    );
  }

  const executions = data?.executions || [];
  const totalCost = executions.reduce((sum, e) => sum + (e.cost || 0), 0);
  const totalTokens = executions.reduce((sum, e) => sum + (e.tokens_used || 0), 0);
  const totalLatencyMs = executions.reduce((sum, e) => sum + (e.duration_ms || 0), 0);
  const avgLatencySec = executions.length > 0 ? (totalLatencyMs / executions.length / 1000) : 0;

  return (
    <div className="h-full flex flex-col overflow-y-auto p-6 gap-6 bg-[var(--color-bg-primary)]">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border)]">
        <div>
          <h3 className="text-lg font-bold text-[var(--color-text-primary)]">Pipeline Diagnostics & Observability</h3>
          <p className="text-xs text-[var(--color-text-muted)]">Real-time LLM telemetry and database-logged parameters</p>
        </div>
        <button
          onClick={() => {
            setLoading(true);
            Promise.all([
              fetchDiagnostics(),
              fetchProvidersHealth()
            ]).finally(() => setLoading(false));
          }}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] transition-colors text-[var(--color-text-primary)] disabled:opacity-55"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Observability Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Total Estimated Cost", value: `$${totalCost.toFixed(5)}`, icon: DollarSign, color: "text-[var(--color-success)] bg-[var(--color-success)]/10" },
          { label: "Total Tokens", value: totalTokens.toLocaleString(), icon: Cpu, color: "text-[var(--color-accent)] bg-[var(--color-accent)]/10" },
          { label: "Total Pipeline Latency", value: `${(totalLatencyMs / 1000).toFixed(2)}s`, icon: Clock, color: "text-[var(--color-info)] bg-[var(--color-info)]/10" },
          { label: "Average Latency/Call", value: `${avgLatencySec.toFixed(2)}s`, icon: Zap, color: "text-[var(--color-warning)] bg-[var(--color-warning)]/10" },
        ].map((m, i) => (
          <div key={i} className="glass-card p-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider">{m.label}</div>
              <div className="text-xl font-bold mt-1 text-[var(--color-text-primary)]">{m.value}</div>
            </div>
            <div className={`p-2.5 rounded-xl ${m.color}`}>
              <m.icon className="w-5 h-5" />
            </div>
          </div>
        ))}
      </div>

      {/* LLM Provider Status Section */}
      <div className="glass-card p-5 flex flex-col gap-4">
        <h4 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 border-b border-[var(--color-border)] pb-2">
          <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
          LLM Provider Health Checks
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {providersHealth ? (
            Object.entries(providersHealth).map(([provider, health]) => {
              const connected = health.connected;
              return (
                <div key={provider} className="glass-card p-4 flex flex-col justify-between border border-[var(--color-border)] relative overflow-hidden group">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-[var(--color-text-primary)]">
                      {health.display_name || provider}
                    </span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                      connected 
                        ? "bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/20" 
                        : "bg-[var(--color-error)]/10 text-[var(--color-error)] border-[var(--color-error)]/20"
                    }`}>
                      {connected ? "Online" : "Offline"}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 text-xs z-10">
                    <div className="flex justify-between">
                      <span className="text-[var(--color-text-muted)]">Model Name:</span>
                      <span className="font-mono text-[var(--color-text-secondary)]">
                        {health.model_name}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--color-text-muted)]">Latency:</span>
                      <span className="font-mono text-[var(--color-text-secondary)]">
                        {connected ? `${health.latency}ms` : "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--color-text-muted)]">HTTP Status:</span>
                      <span className={`font-mono ${
                        connected ? "text-[var(--color-success)]" : "text-[var(--color-error)]"
                      }`}>
                        {health.last_status || "Unknown"}
                      </span>
                    </div>
                    {health.last_error && (
                      <div className="mt-1.5 pt-1.5 border-t border-[var(--color-border)]/50 text-[10px] text-[var(--color-error)] font-mono truncate" title={health.last_error}>
                        {health.last_error}
                      </div>
                    )}
                  </div>
                  {/* Subtle background glow effect */}
                  <div className={`absolute top-0 right-0 w-24 h-24 rounded-full filter blur-[40px] opacity-10 pointer-events-none -mr-8 -mt-8 transition-all duration-300 group-hover:scale-125 ${
                    connected ? "bg-[var(--color-success)]" : "bg-[var(--color-error)]"
                  }`} />
                </div>
              );
            })
          ) : (
            <div className="col-span-4 text-center py-4 text-xs text-[var(--color-text-muted)] animate-pulse">
              Fetching provider health checks...
            </div>
          )}
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Executions Table (Left/Center) */}
        <div className="lg:col-span-2 glass-card p-5 flex flex-col gap-4 overflow-hidden min-h-[300px]">
          <h4 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-[var(--color-accent)]" />
            Agent Execution Logs (PostgreSQL)
          </h4>
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)]">
                  <th className="py-2.5 font-bold">Stage/Agent</th>
                  <th className="py-2.5 font-bold">Model Name</th>
                  <th className="py-2.5 font-bold">Tokens (In/Out)</th>
                  <th className="py-2.5 font-bold">Latency</th>
                  <th className="py-2.5 font-bold">Cost</th>
                  <th className="py-2.5 font-bold text-center">Inspect</th>
                </tr>
              </thead>
              <tbody>
                {executions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[var(--color-text-muted)]">
                      No Postgres telemetry records yet for this session.
                    </td>
                  </tr>
                ) : (
                  executions.map((e, idx) => (
                    <tr key={idx} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-hover)]/30">
                      <td className="py-3 capitalize font-semibold text-[var(--color-text-primary)]">
                        {e.agent_name.replace("_", " ")}
                      </td>
                      <td className="py-3 text-[var(--color-text-secondary)] font-mono text-[10px]">
                        {e.model_name || "fallback"}
                      </td>
                      <td className="py-3 text-[var(--color-text-secondary)]">
                        {e.tokens_in !== undefined ? `${e.tokens_in} / ${e.tokens_out}` : `${e.tokens_used}`}
                      </td>
                      <td className="py-3 text-[var(--color-text-secondary)]">
                        {e.latency ? `${(e.latency / 1000).toFixed(2)}s` : `${(e.duration_ms / 1000).toFixed(2)}s`}
                      </td>
                      <td className="py-3 text-[var(--color-success)] font-medium">
                        ${e.cost !== undefined ? e.cost.toFixed(5) : "0.000"}
                      </td>
                      <td className="py-3 text-center">
                        <button
                          onClick={() => setSelectedExecution(e)}
                          className="inline-flex items-center justify-center p-1.5 rounded bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-accent)]/20 text-[var(--color-accent)] transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pipeline Output Statistics (Right) */}
        <div className="glass-card p-5 flex flex-col gap-4">
          <h4 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
            <Database className="w-4 h-4 text-[var(--color-info)]" />
            Active Pipeline State
          </h4>
          <div className="flex flex-col gap-3.5 text-xs">
            <div className="pb-2 border-b border-[var(--color-border)]">
              <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">User Topic</span>
              <span className="font-semibold text-sm text-[var(--color-text-primary)] mt-0.5 block">{data?.topic || "Extracting..."}</span>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-2 border-b border-[var(--color-border)]">
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Search Queries</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.search_queries?.length || 0} generated</span>
              </div>
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Search Results</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.search_results?.length || 0} indexed</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-2 border-b border-[var(--color-border)]">
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Browser URLs</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.browser_urls?.length || 0} visited</span>
              </div>
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Reader Docs</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.reader_documents?.length || 0} extracted</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-2 border-b border-[var(--color-border)]">
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Claims Generated</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.claims_generated?.length || 0} extracted</span>
              </div>
              <div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Citations Collected</span>
                <span className="font-semibold text-[var(--color-text-primary)] text-sm">{data?.citations_collected?.length || 0} verified</span>
              </div>
            </div>

            {data?.writer_prompt && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Writer Prompt</span>
                <CollapsibleJsonCard title="Writer Prompt" data={data.writer_prompt} />
              </div>
            )}

            {data?.raw_llm_output && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Raw LLM Output (Writer)</span>
                <CollapsibleJsonCard title="Raw Writer Output" data={data.raw_llm_output} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Citation Agent Diagnostics Section */}
      <div className="glass-card p-5 flex flex-col gap-4">
        <h4 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 border-b border-[var(--color-border)] pb-2">
          <ShieldAlert className="w-4 h-4 text-[var(--color-warning)]" />
          Citation Agent Diagnostics
        </h4>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-xs font-mono">
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Citation Agent Input</span>
            <CollapsibleJsonCard title="Citation Input" data={data?.citation_agent_input} />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Citation Agent Output</span>
            <CollapsibleJsonCard title="Citation Output" data={data?.citation_agent_output} />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider block">Citation Generation Errors</span>
            <div className={`p-3 border rounded overflow-y-auto max-h-48 whitespace-pre-wrap ${data?.citation_agent_error ? "bg-[var(--color-error)]/10 border-[var(--color-error)]/30 text-[var(--color-error)] font-bold" : "bg-[var(--color-bg-secondary)] border-[var(--color-border)] text-[var(--color-text-muted)]"}`}>
              {data?.citation_agent_error || "No errors logged."}
            </div>
          </div>
        </div>
      </div>

      {/* Inspection Modal */}
      {selectedExecution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-card w-full max-w-3xl flex flex-col max-h-[85vh] overflow-hidden shadow-2xl border border-[var(--color-border-active)]">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-[var(--color-border)]">
              <div>
                <h4 className="text-sm font-bold capitalize text-[var(--color-text-primary)]">
                  Inspect Stage: {selectedExecution.agent_name.replace("_", " ")}
                </h4>
                <p className="text-[10px] text-[var(--color-text-muted)]">
                  Executed at {new Date(selectedExecution.created_at).toLocaleTimeString()} using model {selectedExecution.model_name || "unknown"}
                </p>
              </div>
              <button
                onClick={() => setSelectedExecution(null)}
                className="text-xs px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-[var(--color-text-muted)] hover:text-white"
              >
                Close
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 text-xs font-mono">
              {selectedExecution.error && (
                <div className="p-3 bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded text-[var(--color-error)]">
                  <span className="font-bold block mb-1">Execution Error:</span>
                  {selectedExecution.error}
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Input Prompt</span>
                <CollapsibleJsonCard title="Execution Input" data={selectedExecution.input_data} defaultExpanded={true} />
              </div>

              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Output / Response</span>
                <CollapsibleJsonCard title="Execution Output" data={selectedExecution.output_data} defaultExpanded={true} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
