"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Sparkles, ChevronDown, Check } from "lucide-react";

interface PromptInputProps {
  onSubmit: (prompt: string, depth: string, maxSources: number, pages?: number, layout?: string, font?: string, visualMode?: string) => void;
  isRunning: boolean;
}

export function PromptInput({ onSubmit, isRunning }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [depth, setDepth] = useState("standard");
  const [maxSources, setMaxSources] = useState(20);
  const [showOptions, setShowOptions] = useState(false);

  // Confirmation Modal State
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmTopic, setConfirmTopic] = useState("");
  const [confirmPages, setConfirmPages] = useState(12);
  const [lengthOption, setLengthOption] = useState("12");
  const [confirmLayout, setConfirmLayout] = useState("Double Column IEEE (Default)");
  const [confirmFont, setConfirmFont] = useState("Times New Roman");
  const [customFont, setCustomFont] = useState("");
  const [confirmVisualMode, setConfirmVisualMode] = useState("Auto Generate");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length >= 10 && !isRunning) {
      setConfirmTopic(prompt);
      setConfirmPages(12);
      setLengthOption("12");
      setConfirmLayout("Double Column IEEE (Default)");
      setConfirmFont("Times New Roman");
      setCustomFont("");
      setConfirmVisualMode("Auto Generate");
      setShowConfirm(true);
    }
  };

  const handleConfirmSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmTopic.trim().length >= 10 && !isRunning) {
      const finalFont = confirmFont === "Custom" ? (customFont || "Arial") : confirmFont;
      onSubmit(confirmTopic, depth, maxSources, confirmPages, confirmLayout, finalFont, confirmVisualMode);
      setShowConfirm(false);
    }
  };

  return (
    <>
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        onSubmit={handleSubmit}
        className="w-full max-w-3xl mx-auto"
      >
        <div className="glass-card glow-accent p-1 transition-all duration-300 focus-within:shadow-[0_0_40px_rgba(99,102,241,0.2)]">
          <div className="flex items-center gap-3 px-4 py-3">
            <Sparkles className="w-5 h-5 text-[var(--color-accent)] shrink-0" />
            <input
              id="research-prompt-input"
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your research topic or question..."
              disabled={isRunning}
              className="flex-1 bg-transparent text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none text-base font-light"
            />
            <button
              id="research-submit-btn"
              type="submit"
              disabled={prompt.trim().length < 10 || isRunning}
              className="shrink-0 flex items-center gap-2 px-5 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-accent-hover)] transition-colors duration-200"
            >
              {isRunning ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              {isRunning ? "Researching..." : "Research"}
            </button>
          </div>

          {/* Options toggle */}
          <div className="px-4 pb-2">
            <button
              type="button"
              onClick={() => setShowOptions(!showOptions)}
              className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            >
              <ChevronDown className={`w-3 h-3 transition-transform ${showOptions ? "rotate-180" : ""}`} />
              Options
            </button>

            {showOptions && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="flex items-center gap-6 mt-2 pt-2 border-t border-[var(--color-border)]"
              >
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--color-text-muted)]">Depth:</label>
                  <select
                    value={depth}
                    onChange={(e) => setDepth(e.target.value)}
                    className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-xs rounded px-2 py-1 border border-[var(--color-border)] outline-none"
                  >
                    <option value="quick">Quick</option>
                    <option value="standard">Standard</option>
                    <option value="deep">Deep</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-[var(--color-text-muted)]">Max Sources:</label>
                  <input
                    type="number"
                    value={maxSources}
                    onChange={(e) => setMaxSources(Number(e.target.value))}
                    min={5}
                    max={100}
                    className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-xs rounded px-2 py-1 w-16 border border-[var(--color-border)] outline-none"
                  />
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </motion.form>

      {/* Confirmation Modal */}
      <AnimatePresence>
        {showConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] p-6 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col gap-4 overflow-y-auto max-h-[90vh]"
            >
              <div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
                  Confirm Research Parameters
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Specify topic details and publication settings before launching ResearchOS agents.
                </p>
              </div>

              <form onSubmit={handleConfirmSubmit} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                    Research Topic
                  </label>
                  <input
                    type="text"
                    value={confirmTopic}
                    onChange={(e) => setConfirmTopic(e.target.value)}
                    required
                    className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2.5 text-sm w-full outline-none focus:border-[var(--color-accent)] transition-colors"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                    Paper Length (Pages)
                  </label>
                  <div className="flex flex-wrap gap-2 mb-1.5">
                    {["6", "8", "10", "12", "13", "15", "Custom"].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setLengthOption(opt);
                          if (opt !== "Custom") {
                            setConfirmPages(Number(opt));
                          }
                        }}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                          lengthOption === opt
                            ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)]"
                            : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:bg-[var(--color-bg-hover)]"
                        }`}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                  {lengthOption === "Custom" && (
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        value={confirmPages}
                        onChange={(e) => setConfirmPages(Number(e.target.value))}
                        required
                        min={1}
                        max={100}
                        className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2.5 text-sm w-24 outline-none focus:border-[var(--color-accent)] text-center font-mono"
                      />
                      <span className="text-xs text-[var(--color-text-muted)]">
                        Enter custom number of pages
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                    Layout Type
                  </label>
                  <select
                    value={confirmLayout}
                    onChange={(e) => setConfirmLayout(e.target.value)}
                    className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2.5 text-sm w-full outline-none focus:border-[var(--color-accent)] transition-colors"
                  >
                    <option value="Single Column">Single Column</option>
                    <option value="Double Column IEEE (Default)">Double Column IEEE (Default)</option>
                    <option value="Triple Column">Triple Column</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                    Font Choice
                  </label>
                  <div className="flex flex-col gap-2">
                    <select
                      value={confirmFont}
                      onChange={(e) => setConfirmFont(e.target.value)}
                      className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2.5 text-sm w-full outline-none focus:border-[var(--color-accent)] transition-colors"
                    >
                      <option value="Times New Roman">Times New Roman</option>
                      <option value="Calibri">Calibri</option>
                      <option value="Arial">Arial</option>
                      <option value="Cambria">Cambria</option>
                      <option value="Georgia">Georgia</option>
                      <option value="User Custom">User Custom</option>
                    </select>
                    {confirmFont === "User Custom" && (
                      <input
                        type="text"
                        placeholder="Enter custom font name (e.g. Courier New)..."
                        value={customFont}
                        onChange={(e) => setCustomFont(e.target.value)}
                        required
                        className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2 text-xs w-full outline-none focus:border-[var(--color-accent)] transition-colors"
                      />
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[var(--color-text-secondary)]">
                    Visuals
                  </label>
                  <select
                    value={confirmVisualMode}
                    onChange={(e) => setConfirmVisualMode(e.target.value)}
                    className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg p-2.5 text-sm w-full outline-none focus:border-[var(--color-accent)] transition-colors"
                  >
                    <option value="Auto Generate">Auto Generate</option>
                    <option value="Manual Upload">Manual Upload</option>
                    <option value="No Visuals">No Visuals</option>
                  </select>
                </div>

                <div className="flex items-center justify-end gap-2 mt-2 pt-3 border-t border-[var(--color-border)]">
                  <button
                    type="button"
                    onClick={() => setShowConfirm(false)}
                    className="px-4 py-2 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] rounded-lg border border-[var(--color-border)] transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 text-xs font-medium text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] rounded-lg shadow-md shadow-[var(--color-accent)]/10 hover:shadow-[var(--color-accent)]/20 transition-all flex items-center gap-1.5"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Confirm & Start
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
