"use client";

import { useResearchStore } from "@/stores/research-store";
import { Hash, DollarSign } from "lucide-react";

export function TokenCounter() {
  const totalTokensIn = useResearchStore((s) => s.totalTokensIn);
  const totalTokensOut = useResearchStore((s) => s.totalTokensOut);
  const totalCost = useResearchStore((s) => s.totalCost);

  const totalTokens = totalTokensIn + totalTokensOut;

  if (totalTokens === 0) return null;

  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1 font-mono text-[10px]">
        <Hash className="w-3 h-3 text-[var(--color-accent)]" />
        <span className="token-pulse" key={totalTokens}>
          {totalTokens.toLocaleString()}
        </span>
        <span className="text-[var(--color-text-muted)]">tok</span>
      </span>
      {totalCost > 0 && (
        <span className="flex items-center gap-1 font-mono text-[10px]">
          <DollarSign className="w-3 h-3 text-[var(--color-success)]" />
          <span>${totalCost.toFixed(4)}</span>
        </span>
      )}
    </div>
  );
}
