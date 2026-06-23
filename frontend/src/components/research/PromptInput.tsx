"use client";

import { useState } from "react";
import { Search, ChevronDown, Check, X } from "lucide-react";

interface PromptInputProps {
  onSubmit: (prompt: string, depth: string, maxSources: number, pages?: number, layout?: string, font?: string, visualMode?: string) => void;
  isRunning: boolean;
}

export function PromptInput({ onSubmit, isRunning }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [depth, setDepth] = useState("standard");
  const [maxSources, setMaxSources] = useState(20);
  const [showOptions, setShowOptions] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("[DEBUG] BUTTON_CLICKED", { prompt: prompt.trim(), promptLength: prompt.trim().length, isRunning, showConfirm });
    if (prompt.trim().length >= 10 && !isRunning) {
      console.log("[DEBUG] MODAL_OPENING");
      setShowConfirm(true);
    } else {
      console.log("[DEBUG] BUTTON_CLICKED BLOCKED", { reason: prompt.trim().length < 10 ? "prompt_too_short" : "is_running" });
    }
  };

  const handleConfirm = () => {
    console.log("[DEBUG] START_RESEARCH_CALLED from handleConfirm", { prompt: prompt.trim(), depth, maxSources, isRunning });
    if (prompt.trim().length >= 10 && !isRunning) {
      onSubmit(prompt, depth, maxSources, 12, "2 Column", "Times New Roman", "Auto Generate");
      setShowConfirm(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="w-full">
        <div className="flex items-center gap-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg px-3 py-2 focus-within:border-[var(--color-border-accent)] transition-colors">
          <Search className="w-3.5 h-3.5 text-[var(--color-text-muted)] shrink-0" />
          <input
            id="research-prompt-input"
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter research topic..."
            disabled={isRunning}
            className="flex-1 bg-transparent text-[var(--color-text-primary)] text-[13px] placeholder:text-[var(--color-text-muted)] outline-none"
          />
          <button
            id="research-submit-btn"
            type="submit"
            disabled={prompt.trim().length < 10 || isRunning}
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--color-accent)] text-white text-[11px] font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[var(--color-accent-hover)] transition-colors"
          >
            {isRunning ? (
              <div className="w-3 h-3 border-[1.5px] border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Search className="w-3 h-3" />
            )}
            {isRunning ? "running" : "research"}
          </button>
        </div>

        <button
          type="button"
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] mt-1.5 ml-1 transition-colors"
        >
          <ChevronDown className={`w-2.5 h-2.5 transition-transform ${showOptions ? "rotate-180" : ""}`} />
          options
        </button>

        {showOptions && (
          <div className="flex items-center gap-4 mt-2 ml-1">
            <div className="flex items-center gap-1.5">
              <label className="text-[10px] text-[var(--color-text-muted)]">depth:</label>
              <select
                value={depth}
                onChange={(e) => setDepth(e.target.value)}
                className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-[10px] rounded px-1.5 py-0.5 border border-[var(--color-border)] outline-none"
              >
                <option value="quick">quick</option>
                <option value="standard">standard</option>
                <option value="deep">deep</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[10px] text-[var(--color-text-muted)]">sources:</label>
              <input
                type="number"
                value={maxSources}
                onChange={(e) => setMaxSources(Number(e.target.value))}
                min={5}
                max={100}
                className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-[10px] rounded px-1.5 py-0.5 w-12 border border-[var(--color-border)] outline-none"
              />
            </div>
          </div>
        )}
      </form>

      {/* Confirm Modal */}
      {showConfirm && (console.log("[DEBUG] MODAL_RENDERED"), (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
              <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">Confirm Research</span>
              <button onClick={() => setShowConfirm(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="px-4 py-4 space-y-3">
              <div>
                <label className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Topic</label>
                <div className="text-[12px] text-[var(--color-text-primary)] mt-0.5">{prompt}</div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div>
                  <span className="text-[var(--color-text-muted)]">Depth: </span>
                  <span className="text-[var(--color-text-primary)]">{depth}</span>
                </div>
                <div>
                  <span className="text-[var(--color-text-muted)]">Sources: </span>
                  <span className="text-[var(--color-text-primary)]">{maxSources}</span>
                </div>
                <div>
                  <span className="text-[var(--color-text-muted)]">Pages: </span>
                  <span className="text-[var(--color-text-primary)]">12</span>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-[var(--color-border)]">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 text-[11px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] rounded-md transition-colors"
              >
                cancel
              </button>
              <button
                onClick={handleConfirm}
                className="flex items-center gap-1.5 px-4 py-1.5 text-[11px] font-medium text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] rounded-md transition-colors"
              >
                <Check className="w-3 h-3" />
                start
              </button>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}
