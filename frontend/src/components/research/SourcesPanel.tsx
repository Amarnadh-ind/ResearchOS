"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Globe } from "lucide-react";
import type { Source } from "@/lib/types";

interface SourcesPanelProps {
  sources: Source[];
}

export function SourcesPanel({ sources: rawSources }: SourcesPanelProps) {
  const sources = Array.isArray(rawSources) ? rawSources : [];
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
        Sources Found: {sources.length}
      </div>

      {sources.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-32 text-[var(--color-text-muted)] text-sm gap-2">
          <Globe className="w-8 h-8 opacity-30" />
          <span>Sources will appear during research</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1.5 text-sm font-medium text-[var(--color-accent)] hover:underline mb-2 focus:outline-none w-fit animate-none"
          >
            <span className="font-mono text-xs">{isExpanded ? "▼" : "▶"}</span>
            <span>Search Results</span>
          </button>
          
          {isExpanded && (
            <div className="flex flex-col gap-3 pl-3 border-l border-[var(--color-border)]">
              {sources.map((source, idx) => {
                let domain = "";
                try {
                  domain = new URL(source.url).hostname;
                } catch {
                  domain = "";
                }
                return (
                  <motion.div
                    key={source.url}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="p-3.5 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] transition-all duration-200 group flex flex-col gap-1 text-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[var(--color-text-primary)] font-medium line-clamp-1 group-hover:text-[var(--color-accent)] transition-colors hover:underline"
                      >
                        {source.title || source.url}
                      </a>
                      <ExternalLink className="w-3.5 h-3.5 text-[var(--color-text-muted)] shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    {domain && (
                      <span className="text-[10px] text-[var(--color-text-muted)] font-mono bg-[var(--color-bg-secondary)] px-1.5 py-0.5 rounded w-fit">
                        {domain}
                      </span>
                    )}
                    <p className="text-xs text-[var(--color-text-muted)] mt-1.5 leading-relaxed">
                      {source.snippet}
                    </p>
                    <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-[var(--color-border)]/40">
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-[var(--color-accent)] hover:underline truncate max-w-[70%]"
                      >
                        {source.url}
                      </a>
                      {source.relevance_score !== undefined && (
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                            Relevance: {(source.relevance_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
