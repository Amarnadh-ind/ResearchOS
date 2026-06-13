"use client";

import { motion } from "framer-motion";
import { BookOpen, ExternalLink, CheckCircle, XCircle } from "lucide-react";
import type { Citation } from "@/lib/types";

interface CitationPanelProps {
  citations: Citation[];
}

export function CitationPanel({ citations }: CitationPanelProps) {
  if (citations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-[var(--color-text-muted)] text-sm gap-2 p-4">
        <BookOpen className="w-8 h-8 opacity-30" />
        <span>Citations generated after writing</span>
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
        Citations ({citations.length})
      </div>
      <div className="flex flex-col gap-2">
        {citations.map((c, i) => (
          <motion.div
            key={c.key}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className="p-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]"
          >
            <div className="flex items-start gap-2">
              <span className="text-xs font-mono font-bold text-[var(--color-accent)] shrink-0">{c.key}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{c.ieee_format}</p>
                <div className="flex items-center gap-2 mt-2">
                  {c.verified ? (
                    <span className="flex items-center gap-1 text-[10px] text-[var(--color-success)]">
                      <CheckCircle className="w-3 h-3" /> Verified
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] text-[var(--color-warning)]">
                      <XCircle className="w-3 h-3" /> Unverified
                    </span>
                  )}
                  {c.url && (
                    <a href={c.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)]">
                      <ExternalLink className="w-3 h-3" /> Source
                    </a>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
