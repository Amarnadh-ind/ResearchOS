"use client";

import { useState, useEffect, useCallback } from "react";
import { Wifi, WifiOff, Timer, RefreshCw } from "lucide-react";

interface ProviderHealth {
  status: string;
  connected: boolean;
  latency: number;
  model_name: string;
  display_name: string;
  provider: string;
}

export function ModelHealthBadges() {
  const [providers, setProviders] = useState<Record<string, ProviderHealth> | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/diagnostics/providers/details");
      if (res.ok) {
        const data = await res.json();
        return data as Record<string, ProviderHealth>;
      }
    } catch {
      // Silently fail - health badges are non-critical
    }
    return null;
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchHealth().then((data) => { if (!cancelled && data) setProviders(data); });
    const interval = setInterval(() => {
      fetchHealth().then((data) => { if (!cancelled && data) setProviders(data); });
    }, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [fetchHealth]);

  if (!providers) return null;

  const entries = Object.entries(providers);
  const onlineCount = entries.filter(([, p]) => p.connected).length;
  const totalCount = entries.length;

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`health-badge ${
          onlineCount === totalCount
            ? "online"
            : onlineCount > 0
            ? "degraded"
            : "offline"
        }`}
      >
        {onlineCount === totalCount ? (
          <Wifi className="w-2.5 h-2.5" />
        ) : (
          <WifiOff className="w-2.5 h-2.5" />
        )}
        <span>{onlineCount}/{totalCount}</span>
      </button>

      {expanded && (
        <div className="absolute top-full right-0 mt-2 w-64 glass-card p-3 z-50 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
              LLM Providers
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); fetchHealth(); }}
              className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)]"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
          <div className="flex flex-col gap-1.5">
            {entries.map(([key, health]) => (
              <div
                key={key}
                className="flex items-center justify-between py-1.5 px-2 rounded-md bg-[var(--color-bg-tertiary)]/50 text-[10px]"
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      health.connected
                        ? "bg-[var(--color-success)]"
                        : health.status === "cooldown"
                        ? "bg-[var(--color-warning)]"
                        : "bg-[var(--color-error)]"
                    }`}
                  />
                  <span className="text-[var(--color-text-primary)] font-medium">
                    {health.display_name || key}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
                  {health.connected && health.latency > 0 && (
                    <span className="flex items-center gap-0.5 font-mono">
                      <Timer className="w-2.5 h-2.5" />
                      {health.latency}ms
                    </span>
                  )}
                  <span className={`px-1 py-0 rounded text-[8px] font-bold uppercase ${
                    health.connected
                      ? "bg-[var(--color-success)]/15 text-[var(--color-success)]"
                      : "bg-[var(--color-error)]/15 text-[var(--color-error)]"
                  }`}>
                    {health.connected ? "ON" : "OFF"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
