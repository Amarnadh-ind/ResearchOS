"use client";

import { useMemo, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import type { Source } from "@/lib/types";

interface SourcesPanelProps {
  sources: Source[];
}

function getDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; }
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [filter, setFilter] = useState("");

  const filtered = useMemo(() => {
    if (!filter) return sources;
    const q = filter.toLowerCase();
    return sources.filter(
      (s) => s.title?.toLowerCase().includes(q) || s.url?.toLowerCase().includes(q) || s.snippet?.toLowerCase().includes(q)
    );
  }, [sources, filter]);

  const grouped = useMemo(() => {
    const map = new Map<string, Source[]>();
    for (const s of filtered) {
      const domain = getDomain(s.url);
      if (!map.has(domain)) map.set(domain, []);
      map.get(domain)!.push(s);
    }
    return Array.from(map.entries());
  }, [filtered]);

  if (sources.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-muted)] text-[11px]">
        No sources collected yet
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-[var(--color-text-muted)]">Sources</span>
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{sources.length}</span>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-6 pr-2 py-1 text-[10px] bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-border-accent)] w-32"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {grouped.map(([domain, items]) => (
          <div key={domain} className="mb-4">
            <div className="flex items-center gap-2 mb-1.5">
              <img
                src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
                alt=""
                className="w-3 h-3 rounded-sm"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
              <span className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                {domain}
              </span>
              <span className="text-[9px] text-[var(--color-text-muted)] font-mono">
                {items.length}
              </span>
            </div>
            {items.map((source, i) => (
              <a
                key={i}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block py-2 px-2.5 rounded-md hover:bg-[var(--color-bg-hover)] transition-colors mb-0.5"
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[11px] font-medium text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] truncate flex-1">
                    {source.title || source.url}
                  </span>
                  {source.relevance_score > 0 && (
                    <span className={`text-[9px] font-mono ${source.relevance_score >= 0.7 ? "text-[var(--color-success)]" : source.relevance_score >= 0.4 ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"}`}>
                      {(source.relevance_score * 100).toFixed(0)}%
                    </span>
                  )}
                  <ExternalLink className="w-2.5 h-2.5 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </div>
                {source.snippet && (
                  <p className="text-[10px] text-[var(--color-text-muted)] line-clamp-2 leading-relaxed">
                    {source.snippet}
                  </p>
                )}
              </a>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
