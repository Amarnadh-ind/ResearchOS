"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AGENT_CONFIG } from "@/lib/types";
import type { AgentEvent, Source } from "@/lib/types";
import { formatTimestamp, preview } from "@/lib/utils";
import {
  Clock,
  Cpu,
  Hash,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Zap,
} from "lucide-react";

// ── Constants ────────────────────────────────────────
const ACTIVITY_MESSAGE_LIMIT = 300;
const VIRTUALIZATION_THRESHOLD = 100;
const VIRTUAL_ITEM_HEIGHT = 72; // Estimated height per collapsed row
const VIRTUAL_OVERSCAN = 8;

interface AgentStreamProps {
  events: AgentEvent[];
  currentAgent: string | null;
}

export function AgentStream({ events, currentAgent }: AgentStreamProps) {
  const filteredEvents = useMemo(() => {
    return events.filter(
      (e) => e.type !== "debug" && e.type !== "progress" && e.type !== "expanded"
    );
  }, [events]);

  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>(
    {}
  );
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredEvents.length]);

  // Track container size for virtualization
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const toggleExpand = useCallback((key: string) => {
    setExpandedItems((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const shouldVirtualize = filteredEvents.length > VIRTUALIZATION_THRESHOLD;

  // ── Virtualization math ──
  const { visibleStart, visibleEnd } = useMemo(() => {
    if (!shouldVirtualize)
      return { visibleStart: 0, visibleEnd: filteredEvents.length };
    const start = Math.max(
      0,
      Math.floor(scrollTop / VIRTUAL_ITEM_HEIGHT) - VIRTUAL_OVERSCAN
    );
    const visible = Math.ceil(containerHeight / VIRTUAL_ITEM_HEIGHT);
    const end = Math.min(
      filteredEvents.length,
      start + visible + VIRTUAL_OVERSCAN * 2
    );
    return { visibleStart: start, visibleEnd: end };
  }, [shouldVirtualize, scrollTop, containerHeight, filteredEvents.length]);

  const handleScroll = useCallback(() => {
    if (scrollRef.current && shouldVirtualize) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, [shouldVirtualize]);

  const visibleEvents = shouldVirtualize
    ? filteredEvents.slice(visibleStart, visibleEnd)
    : filteredEvents;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex flex-col gap-0.5 p-4 overflow-y-auto h-full"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          Agent Activity
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
            {filteredEvents.length} events
          </span>
          {shouldVirtualize && (
            <span className="text-[9px] bg-[var(--color-warning)]/15 text-[var(--color-warning)] px-1.5 py-0.5 rounded font-mono">
              VIRTUALIZED
            </span>
          )}
        </div>
      </div>

      {/* Virtualization spacer (top) */}
      {shouldVirtualize && visibleStart > 0 && (
        <div
          style={{ height: visibleStart * VIRTUAL_ITEM_HEIGHT }}
          className="shrink-0"
        />
      )}

      <AnimatePresence initial={false}>
        {visibleEvents.map((event, localIdx) => {
          const idx = shouldVirtualize
            ? visibleStart + localIdx
            : localIdx;
          return (
            <ActivityRow
              key={`${event.agent}-${event.type}-${idx}`}
              event={event}
              idx={idx}
              isExpanded={!!expandedItems[`row-${idx}`]}
              onToggle={() => toggleExpand(`row-${idx}`)}
            />
          );
        })}
      </AnimatePresence>

      {/* Virtualization spacer (bottom) */}
      {shouldVirtualize && visibleEnd < filteredEvents.length && (
        <div
          style={{
            height: (filteredEvents.length - visibleEnd) * VIRTUAL_ITEM_HEIGHT,
          }}
          className="shrink-0"
        />
      )}

      {/* Running indicator */}
      {currentAgent && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 py-2 px-3 text-sm"
        >
          <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-pulse" />
          <span className="text-[var(--color-text-muted)]">
            {AGENT_CONFIG[currentAgent]?.icon}{" "}
            <span style={{ color: AGENT_CONFIG[currentAgent]?.color }}>
              {AGENT_CONFIG[currentAgent]?.label}
            </span>{" "}
            is working...
          </span>
        </motion.div>
      )}

      {filteredEvents.length === 0 && !currentAgent && (
        <div className="flex items-center justify-center h-32 text-[var(--color-text-muted)] text-sm">
          Waiting for research to begin...
        </div>
      )}
    </div>
  );
}

// ── Individual Activity Row ────────────────────────────
interface ActivityRowProps {
  event: AgentEvent;
  idx: number;
  isExpanded: boolean;
  onToggle: () => void;
}

function ActivityRow({ event, idx, isExpanded, onToggle }: ActivityRowProps) {
  const config = AGENT_CONFIG[event.agent] || {
    label: event.agent,
    color: "var(--color-text-muted)",
    icon: "⚙️",
  };

  const isError = event.type === "error";
  const isComplete = event.type === "completed";
  const isDebug = event.type === "debug";
  const data = (event.data || {}) as Record<string, unknown>;

  // Extract metadata fields for compact display
  const provider = (data.provider as string) || "";
  const model = (data.model as string) || "";
  const latency =
    (data.latency as number) || (data.latency_ms as number) || (data.duration_ms as number) || 0;
  const tokenCount =
    (data.token_count as number) ||
    ((data.tokens_in as number) || 0) + ((data.tokens_out as number) || 0) ||
    0;
  const responseLength = (data.response_length as number) || 0;
  const cost = data.cost as number | undefined;

  // Get preview text (if available)
  const responsePreview =
    (data.response_preview as string) || (data.response as string) || "";
  const promptPreview =
    (data.prompt_preview as string) || "";

  // Determine if this row has full-output data worth expanding
  const hasExpandableContent =
    isDebug ||
    responsePreview.length > 0 ||
    promptPreview.length > 0 ||
    Object.keys(data).some(
      (k) =>
        !isMetadataKey(k) &&
        typeof data[k] === "object" &&
        data[k] !== null
    );

  // Check for search results
  const searchResults = data.results || data.search_results;
  const hasSearchResults = Array.isArray(searchResults);
  const resultsCount = hasSearchResults
    ? (searchResults as unknown[]).length
    : data._count
    ? (data._count as number)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className={`rounded-lg text-xs border ${
        isError
          ? "bg-[var(--color-error)]/5 border-[var(--color-error)]/20"
          : isComplete
          ? "bg-[var(--color-success)]/5 border-[var(--color-success)]/10"
          : "bg-[var(--color-bg-secondary)]/30 border-[var(--color-border)]/50 hover:bg-[var(--color-bg-hover)]"
      }`}
    >
      {/* ── Compact header: always visible ── */}
      <div
        className="flex items-center gap-2 py-1.5 px-3 cursor-pointer select-none"
        onClick={hasExpandableContent ? onToggle : undefined}
      >
        {/* Agent icon + label */}
        <span className="text-sm shrink-0">{config.icon}</span>
        <span
          className="font-semibold text-[11px] shrink-0"
          style={{ color: config.color }}
        >
          {config.label}
        </span>

        {/* Status badge */}
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
            isComplete
              ? "bg-[var(--color-success)]/15 text-[var(--color-success)]"
              : isError
              ? "bg-[var(--color-error)]/15 text-[var(--color-error)]"
              : "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
          }`}
        >
          {event.type}
        </span>

        {/* ── Metadata chips ── */}
        <div className="flex items-center gap-1.5 ml-auto flex-wrap justify-end">
          {provider && (
            <MetadataChip
              icon={<Cpu className="w-2.5 h-2.5" />}
              value={`${provider}${model ? `:${model.split("/").pop()}` : ""}`}
            />
          )}
          {latency > 0 && (
            <MetadataChip
              icon={<Clock className="w-2.5 h-2.5" />}
              value={latency >= 1000 ? `${(latency / 1000).toFixed(1)}s` : `${latency}ms`}
            />
          )}
          {tokenCount > 0 && (
            <MetadataChip
              icon={<Hash className="w-2.5 h-2.5" />}
              value={`${tokenCount} tok`}
            />
          )}
          {resultsCount > 0 && (
            <MetadataChip
              icon={<Zap className="w-2.5 h-2.5" />}
              value={`${resultsCount} results`}
            />
          )}
          {cost !== undefined && cost > 0 && (
            <MetadataChip value={`$${cost.toFixed(4)}`} />
          )}
        </div>

        {/* Timestamp */}
        <span className="text-[9px] text-[var(--color-text-muted)] shrink-0 font-mono ml-2">
          {event.timestamp ? formatTimestamp(event.timestamp) : ""}
        </span>

        {/* Expand toggle */}
        {hasExpandableContent && (
          <span className="text-[var(--color-text-muted)] shrink-0">
            {isExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </span>
        )}
      </div>

      {/* ── Preview line (collapsed) ── */}
      {!isExpanded && responsePreview && (
        <div className="px-3 pb-1.5 -mt-0.5">
          <span className="text-[10px] text-[var(--color-text-muted)] leading-tight line-clamp-1 font-mono">
            {preview(responsePreview, ACTIVITY_MESSAGE_LIMIT)}
          </span>
        </div>
      )}

      {/* ── Error message (always visible for errors) ── */}
      {isError && !!data.error && (
        <div className="px-3 pb-1.5">
          <span className="text-[10px] text-[var(--color-error)] font-mono">
            {preview(String(data.error || ""), ACTIVITY_MESSAGE_LIMIT)}
          </span>
        </div>
      )}

      {/* ── Expanded content ── */}
      {isExpanded && (
        <div className="px-3 pb-2 border-t border-[var(--color-border)]/30 mt-0.5 pt-2 flex flex-col gap-2">
          {/* Show Full Output toggle header */}
          <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
            <Eye className="w-3 h-3" />
            <span className="font-semibold uppercase tracking-wider">
              Full Output
            </span>
            {responseLength > 0 && (
              <span className="font-mono opacity-60">
                ({responseLength.toLocaleString()} chars)
              </span>
            )}
          </div>

          {/* Prompt preview */}
          {promptPreview && (
            <div className="flex flex-col gap-1">
              <span className="text-[9px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Prompt
              </span>
              <pre className="text-[10px] text-[var(--color-text-secondary)] bg-[var(--color-bg-primary)] border border-[var(--color-border)] p-2 rounded font-mono whitespace-pre-wrap max-h-24 overflow-y-auto">
                {preview(promptPreview, ACTIVITY_MESSAGE_LIMIT)}
              </pre>
            </div>
          )}

          {/* Response preview */}
          {responsePreview && (
            <div className="flex flex-col gap-1">
              <span className="text-[9px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Response
              </span>
              <pre className="text-[10px] text-[var(--color-text-primary)] bg-[var(--color-bg-primary)] border border-[var(--color-border)] p-2 rounded font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
                {preview(responsePreview, ACTIVITY_MESSAGE_LIMIT)}
              </pre>
              {responseLength > ACTIVITY_MESSAGE_LIMIT && (
                <span className="text-[9px] text-[var(--color-accent)] italic">
                  Full output available in Sources / Paper / Diagnostics tabs
                </span>
              )}
            </div>
          )}

          {/* Search results (collapsed by default) */}
          {hasSearchResults && (
            <SearchResultsSection
              results={searchResults as Source[]}
            />
          )}

          {/* Other data fields (compact) */}
          <CompactDataView
            data={data}
            excludeKeys={[
              "provider", "model", "latency", "latency_ms", "duration_ms",
              "tokens_in", "tokens_out", "token_count", "cost",
              "response_preview", "response_length", "prompt_preview",
              "prompt_length", "response", "prompt", "error",
              "results", "search_results", "topic",
              "response_length", "writer_prompt_preview", "writer_prompt_length",
              "raw_llm_output_preview", "raw_llm_output_length",
              "content_preview", "content_length",
              "content_markdown_preview", "content_markdown_length",
            ]}
          />
        </div>
      )}
    </motion.div>
  );
}

// ── Metadata Chip ────────────────────────────────────
function MetadataChip({
  icon,
  value,
}: {
  icon?: React.ReactNode;
  value: string;
}) {
  return (
    <span className="inline-flex items-center gap-0.5 text-[9px] text-[var(--color-text-muted)] bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded font-mono">
      {icon}
      {value}
    </span>
  );
}

// ── Compact Data View ────────────────────────────────
function CompactDataView({
  data,
  excludeKeys,
}: {
  data: Record<string, unknown>;
  excludeKeys: string[];
}) {
  const entries = Object.entries(data).filter(
    ([k]) => !excludeKeys.includes(k) && !k.startsWith("_")
  );

  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => {
        const display =
          typeof value === "string"
            ? preview(value, 80)
            : typeof value === "number" || typeof value === "boolean"
            ? String(value)
            : typeof value === "object" && value !== null
            ? Array.isArray(value)
              ? `[${value.length} items]`
              : `{${Object.keys(value).length} keys}`
            : String(value);

        return (
          <span
            key={key}
            className="text-[9px] text-[var(--color-text-muted)] bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded"
          >
            <span className="font-semibold">{key}:</span>{" "}
            <span className="text-[var(--color-text-secondary)]">
              {display}
            </span>
          </span>
        );
      })}
    </div>
  );
}

// ── Search Results Section ───────────────────────────
function SearchResultsSection({ results }: { results: Source[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex flex-col gap-1.5">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-[10px] text-[var(--color-accent)] font-semibold hover:underline focus:outline-none"
      >
        {isOpen ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        Search Results ({results.length})
      </button>
      {isOpen && (
        <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
          {results.map((res, i) => {
            let hostname = "";
            try {
              hostname = new URL(res.url).hostname;
            } catch {
              hostname = "";
            }
            return (
              <div
                key={i}
                className="p-2 rounded border border-[var(--color-border)] bg-[var(--color-bg-primary)] flex flex-col gap-0.5 text-[10px]"
              >
                <div className="flex items-center justify-between gap-2">
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-[var(--color-text-primary)] hover:text-[var(--color-accent)] hover:underline line-clamp-1"
                  >
                    {res.title || res.url}
                  </a>
                  {hostname && (
                    <span className="text-[9px] text-[var(--color-text-muted)] font-mono bg-[var(--color-bg-tertiary)] px-1 py-0.5 rounded shrink-0">
                      {hostname}
                    </span>
                  )}
                </div>
                <p className="text-[var(--color-text-muted)] line-clamp-1 text-[9px]">
                  {res.snippet}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────
function isMetadataKey(key: string): boolean {
  const metaKeys = new Set([
    "provider", "model", "tokens_in", "tokens_out", "token_count",
    "cost", "latency", "latency_ms", "duration_ms", "response_length",
    "status", "topic", "agent", "type", "error",
  ]);
  return metaKeys.has(key);
}
