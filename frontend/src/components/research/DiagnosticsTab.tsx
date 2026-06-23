"use client";

import { useEffect, useState } from "react";
import { useResearchStore } from "@/stores/research-store";
import { RefreshCw, Activity, Cpu, Zap, Wifi, Clock } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ProviderHealth {
  status: string;
  connected: boolean;
  latency: number;
  model: string;
  models_tried?: string[];
  error?: string;
}

interface SessionDiag {
  session_id: string;
  topic: string;
  search_results: unknown[];
  citations_collected: unknown[];
  final_paper: unknown;
  executions: unknown[];
}

export function DiagnosticsTab() {
  const sessionId = useResearchStore((s) => s.sessionId);
  const [providers, setProviders] = useState<Record<string, ProviderHealth>>({});
  const [sessionDiag, setSessionDiag] = useState<SessionDiag | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      try {
        const res = await fetch(`${API_URL}/api/diagnostics/providers/details`, { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setProviders(data.providers || {});
          setLastRefresh(new Date());
        }
      } catch {}
    };
    load();
    const interval = setInterval(load, 15000);
    return () => { clearInterval(interval); controller.abort(); };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const controller = new AbortController();
    const load = async () => {
      try {
        const res = await fetch(`${API_URL}/api/research/${sessionId}/diagnostics`, { signal: controller.signal });
        if (res.ok) setSessionDiag(await res.json());
      } catch {}
    };
    load();
    return () => controller.abort();
  }, [sessionId]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const [provRes, diagRes] = await Promise.all([
        fetch(`${API_URL}/api/diagnostics/providers/details`),
        sessionId ? fetch(`${API_URL}/api/research/${sessionId}/diagnostics`) : Promise.resolve(null),
      ]);
      if (provRes.ok) {
        const data = await provRes.json();
        setProviders(data.providers || {});
      }
      if (diagRes?.ok) setSessionDiag(await diagRes.json());
      setLastRefresh(new Date());
    } catch {}
    setLoading(false);
  };

  const providerEntries = Object.entries(providers);
  const onlineCount = providerEntries.filter(([, p]) => p.connected).length;

  if (providerEntries.length === 0 && !sessionDiag) {
    return <DiagnosticsSkeleton />;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-[var(--color-text-muted)]">Diagnostics</span>
          {lastRefresh && (
            <span className="text-[9px] text-[var(--color-text-muted)] font-mono">
              {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-3 space-y-4">
        {/* Provider Health */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <div className="text-[9px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
              Providers
            </div>
            <div className="flex items-center gap-1">
              <Wifi className="w-3 h-3 text-[var(--color-success)]" />
              <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
                {onlineCount}/{providerEntries.length}
              </span>
            </div>
          </div>
          <div className="space-y-1">
            {providerEntries.map(([name, p]) => (
              <div key={name} className="flex items-center gap-2 sm:gap-3 py-1.5 px-2 sm:px-2.5 rounded bg-[var(--color-bg-secondary)]/30 border border-[var(--color-border)]">
                <div className={`status-dot ${p.connected ? "completed" : "error"}`} />
                <span className="text-[10px] sm:text-[11px] font-medium text-[var(--color-text-primary)] w-16 sm:w-20 truncate">{name}</span>
                <span className="text-[9px] sm:text-[10px] text-[var(--color-text-muted)] font-mono flex-1 truncate">{p.model}</span>
                {p.latency > 0 && (
                  <span className="flex items-center gap-0.5 text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono">
                    <Clock className="w-2.5 h-2.5" />
                    {p.latency}ms
                  </span>
                )}
                <span className={`text-[8px] sm:text-[9px] font-mono ${p.connected ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}`}>
                  {p.status}
                </span>
              </div>
            ))}
            {providerEntries.length === 0 && (
              <div className="text-[10px] text-[var(--color-text-muted)] italic py-2">No provider data</div>
            )}
          </div>
        </section>

        {/* Session Diagnostics */}
        {sessionDiag && (
          <>
            <section>
              <div className="text-[9px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                Session
              </div>
              <div className="grid grid-cols-3 gap-2">
                <MetricCard icon={<Activity className="w-3 h-3" />} label="Sources" value={sessionDiag.search_results?.length ?? 0} />
                <MetricCard icon={<Zap className="w-3 h-3" />} label="Citations" value={sessionDiag.citations_collected?.length ?? 0} />
                <MetricCard icon={<Cpu className="w-3 h-3" />} label="Executions" value={sessionDiag.executions?.length ?? 0} />
              </div>
            </section>

            {/* Agent Executions */}
            {sessionDiag.executions && sessionDiag.executions.length > 0 && (
              <section>
                <div className="text-[9px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                  Executions
                </div>
                <div className="space-y-0.5">
                  {(sessionDiag.executions as Record<string, unknown>[]).map((ex, i) => (
                    <div key={i} className="flex items-center gap-2 py-1.5 px-2 sm:px-2.5 rounded hover:bg-[var(--color-bg-hover)] text-[9px] sm:text-[10px]">
                      <span className="text-[var(--color-text-primary)] font-medium w-20 sm:w-24 truncate">{String(ex.agent_name)}</span>
                      <span className={`px-1.5 py-0 rounded text-[8px] sm:text-[9px] font-mono ${
                        ex.status === "success" ? "bg-[var(--color-success)]/10 text-[var(--color-success)]" :
                        ex.status === "error" ? "bg-[var(--color-error)]/10 text-[var(--color-error)]" :
                        "bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
                      }`}>
                        {String(ex.status)}
                      </span>
                      {ex.model_name ? (
                        <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono truncate flex-1">{String(ex.model_name)}</span>
                      ) : null}
                      {ex.duration_ms ? (
                        <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono">{Number(ex.duration_ms)}ms</span>
                      ) : null}
                      {ex.tokens_used ? (
                        <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono">{Number(ex.tokens_used)} tok</span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Search Results */}
            {sessionDiag.search_results && sessionDiag.search_results.length > 0 && (
              <section>
                <div className="text-[9px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                  Search Results ({sessionDiag.search_results.length})
                </div>
                <div className="space-y-0.5">
                  {(sessionDiag.search_results as Record<string, unknown>[]).slice(0, 10).map((r, i) => (
                    <div key={i} className="py-1 px-2.5 rounded hover:bg-[var(--color-bg-hover)]">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] sm:text-[10px] text-[var(--color-text-primary)] truncate flex-1">{String(r.title || r.url)}</span>
                        {r.relevance_score ? (
                          <span className="text-[8px] sm:text-[9px] text-[var(--color-text-muted)] font-mono">{(Number(r.relevance_score) * 100).toFixed(0)}%</span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="p-2 sm:p-2.5 rounded bg-[var(--color-bg-secondary)]/30 border border-[var(--color-border)]">
      <div className="flex items-center gap-1.5 text-[var(--color-text-muted)] mb-1">
        {icon}
        <span className="text-[8px] sm:text-[9px] uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-base sm:text-lg font-semibold text-[var(--color-text-primary)] font-mono">{value}</div>
    </div>
  );
}

function DiagnosticsSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-[var(--color-border)]">
        <div className="skeleton skeleton-text w-20" />
      </div>
      <div className="flex-1 px-4 py-3 space-y-4">
        <div>
          <div className="skeleton skeleton-text w-16 mb-2" />
          <div className="space-y-1">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        </div>
        <div>
          <div className="skeleton skeleton-text w-12 mb-2" />
          <div className="grid grid-cols-3 gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
