"use client";

import { useMemo, useState } from "react";
import { Download, Copy, Check, ExternalLink, FileText, Eye } from "lucide-react";
import type { Paper } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PaperViewerProps {
  markdown: string;
  title: string;
  paper?: Paper | null;
  isStreaming?: boolean;
  sessionId?: string | null;
}

export function PaperViewer({ markdown, title, paper, isStreaming, sessionId }: PaperViewerProps) {
  const [copied, setCopied] = useState(false);
  const [showPdf, setShowPdf] = useState(false);

  const content = useMemo(() => {
    if (markdown && markdown.trim()) return markdown;
    if (paper) return buildPaperMarkdown(paper);
    return "";
  }, [markdown, paper]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!content && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--color-text-muted)]">
        <FileText className="w-10 h-10 opacity-20" />
        <span className="text-[11px]">No paper content yet</span>
      </div>
    );
  }

  if (isStreaming && !content) {
    return <PaperViewerSkeleton />;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[11px] font-medium text-[var(--color-text-muted)] truncate">
            {paper?.title || title || "Paper"}
          </span>
          {isStreaming && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--color-accent-subtle)] text-[var(--color-accent)] font-mono shrink-0">
              streaming
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            {copied ? <Check className="w-3 h-3 text-[var(--color-success)]" /> : <Copy className="w-3 h-3" />}
            <span className="hidden sm:inline">{copied ? "copied" : "copy"}</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <Download className="w-3 h-3" />
            <span className="hidden sm:inline">.md</span>
          </button>
          {paper && sessionId && (
            <button
              onClick={() => setShowPdf(!showPdf)}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors ${
                showPdf
                  ? "text-[var(--color-accent)] bg-[var(--color-accent-subtle)]"
                  : "text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)]"
              }`}
            >
              <Eye className="w-3 h-3" />
              <span className="hidden sm:inline">pdf</span>
            </button>
          )}
          {paper && sessionId && (
            <a
              href={`${API_URL}/api/research/${sessionId}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Content area */}
      {showPdf && paper && sessionId ? (
        <div className="flex-1 overflow-hidden">
          <iframe
            src={`${API_URL}/api/research/${sessionId}/preview`}
            className="w-full h-full border-0"
            title="PDF Preview"
          />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6">
          <article className="max-w-2xl mx-auto">
            {paper?.title && (
              <h1 className="text-lg sm:text-xl font-semibold text-[var(--color-text-primary)] mb-3 leading-tight">
                {paper.title}
              </h1>
            )}
            {paper?.authors && paper.authors.length > 0 && (
              <p className="text-[11px] text-[var(--color-text-muted)] mb-4">
                {paper.authors.join(", ")}
              </p>
            )}
            {paper?.abstract && (
              <div className="mb-6 p-3 sm:p-4 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
                <div className="text-[9px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                  Abstract
                </div>
                <p className="text-[12px] text-[var(--color-text-secondary)] leading-relaxed">
                  {paper.abstract}
                </p>
              </div>
            )}
            <div className="prose prose-invert prose-sm max-w-none">
              <MarkdownContent content={content} isStreaming={isStreaming} />
            </div>
          </article>
        </div>
      )}
    </div>
  );
}

function MarkdownContent({ content, isStreaming }: { content: string; isStreaming?: boolean }) {
  const lines = content.split("\n");

  return (
    <div className={`text-[12px] text-[var(--color-text-secondary)] leading-[1.8] ${isStreaming ? "streaming-cursor" : ""}`}>
      {lines.map((line, i) => {
        const trimmed = line.trim();

        // Empty lines
        if (!trimmed) {
          return <div key={i} className="h-3" />;
        }

        // Headers
        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={i} className="text-[13px] font-semibold text-[var(--color-text-primary)] mt-5 mb-2">
              {renderInline(trimmed.slice(4))}
            </h3>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h2 key={i} className="text-[14px] font-semibold text-[var(--color-text-primary)] mt-7 mb-2">
              {renderInline(trimmed.slice(3))}
            </h2>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h1 key={i} className="text-[18px] font-semibold text-[var(--color-text-primary)] mb-3">
              {renderInline(trimmed.slice(2))}
            </h1>
          );
        }

        // List items
        if (trimmed.startsWith("- ")) {
          return (
            <div key={i} className="ml-4 mb-0.5 text-[12px]">
              <span className="mr-2 text-[var(--color-text-muted)]">{"\u2022"}</span>
              {renderInline(trimmed.slice(2))}
            </div>
          );
        }

        // Numbered list
        const numMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
        if (numMatch) {
          return (
            <div key={i} className="ml-4 mb-0.5 text-[12px]">
              <span className="mr-2 text-[var(--color-text-muted)] font-mono text-[10px]">{numMatch[1]}.</span>
              {renderInline(numMatch[2])}
            </div>
          );
        }

        // Regular paragraph
        return (
          <p key={i} className="mb-2">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  // Process bold and inline code
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Inline code
    const codeMatch = remaining.match(/`(.+?)`/);
    // Italic
    const italicMatch = remaining.match(/\*(.+?)\*/);

    const matches = [
      boldMatch ? { type: "bold" as const, index: boldMatch.index!, match: boldMatch } : null,
      codeMatch ? { type: "code" as const, index: codeMatch.index!, match: codeMatch } : null,
      italicMatch ? { type: "italic" as const, index: italicMatch.index!, match: italicMatch } : null,
    ].filter(Boolean) as { type: "bold" | "code" | "italic"; index: number; match: RegExpMatchArray }[];

    if (matches.length === 0) {
      parts.push(remaining);
      break;
    }

    const first = matches.sort((a, b) => a.index - b.index)[0];

    if (first.index > 0) {
      parts.push(remaining.slice(0, first.index));
    }

    if (first.type === "bold") {
      parts.push(
        <strong key={keyIdx++} className="text-[var(--color-text-primary)] font-medium">
          {first.match[1]}
        </strong>
      );
    } else if (first.type === "code") {
      parts.push(
        <code key={keyIdx++} className="text-[11px] px-1 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-accent)] font-mono">
          {first.match[1]}
        </code>
      );
    } else if (first.type === "italic") {
      parts.push(<em key={keyIdx++}>{first.match[1]}</em>);
    }

    remaining = remaining.slice(first.index + first.match[0].length);
  }

  return <>{parts}</>;
}

function buildPaperMarkdown(paper: Paper): string {
  const parts: string[] = [];
  if (paper.title) parts.push(`# ${paper.title}\n`);
  if (paper.authors?.length) parts.push(`**Authors:** ${paper.authors.join(", ")}\n`);
  if (paper.abstract) parts.push(`## Abstract\n\n${paper.abstract}\n`);
  if (paper.sections?.length) {
    for (const s of paper.sections) {
      parts.push(`## ${s.heading}\n\n${s.content}\n`);
    }
  }
  if (paper.references?.length) {
    parts.push(`## References\n`);
    paper.references.forEach((r, i) => parts.push(`${i + 1}. ${r}`));
  }
  return parts.join("\n");
}

function PaperViewerSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-[var(--color-border)]">
        <div className="skeleton skeleton-text w-48" />
      </div>
      <div className="flex-1 px-6 py-6 overflow-hidden">
        <div className="max-w-2xl mx-auto space-y-4">
          <div className="skeleton skeleton-text w-64 h-5" />
          <div className="skeleton skeleton-text w-40" />
          <div className="skeleton skeleton-card" />
          <div className="space-y-2">
            <div className="skeleton skeleton-text w-full" />
            <div className="skeleton skeleton-text w-5/6" />
            <div className="skeleton skeleton-text w-full" />
            <div className="skeleton skeleton-text w-3/4" />
          </div>
          <div className="space-y-2">
            <div className="skeleton skeleton-text w-full" />
            <div className="skeleton skeleton-text w-4/5" />
            <div className="skeleton skeleton-text w-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
