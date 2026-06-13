"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Download, Copy, Check, Plus, Image as ImageIcon, 
  BarChart3, Grid, Network, Upload, Sparkles, Type, Layout, Trash2,
  ZoomIn, ZoomOut, Eye, Edit3, FileCode
} from "lucide-react";
import { useResearchStore } from "@/stores/research-store";
import type { Paper, PaperSection } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Block {
  id: string;
  type: "title" | "authors" | "affiliation" | "abstract" | "keywords" | "heading" | "subheading" | "paragraph" | "visual" | "references";
  content: string;
  visualType?: "image" | "graph" | "heatmap" | "diagram" | "upload" | "visualization";
  caption?: string;
  metadata?: Record<string, unknown>;
}

type LayoutType = "1 Column" | "2 Column" | "Multi Column";

interface EditablePaperSection {
  heading: string;
  content: string;
  subsections: EditablePaperSection[];
}

interface EditablePaperData {
  title: string;
  authors: string[];
  abstract: string;
  keywords: string[];
  sections: EditablePaperSection[];
  references: string[];
  layout: LayoutType;
  font: string;
}

interface PaperViewerProps {
  markdown: string;
  title: string;
  paper?: Paper | null;
}

function generateStableId(prefix: string, content: string, index: number): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    hash = (hash << 5) - hash + content.charCodeAt(i);
    hash |= 0;
  }
  return `${prefix}-${hash.toString(36)}-${index}`;
}

function parseMarkdownToBlocks(md: string): Block[] {
  const parsed: Block[] = [];
  const lines = md.split("\n");
  let currentParagraph = "";
  let idx = 0;
  
  const flushParagraph = () => {
    if (currentParagraph.trim()) {
      idx += 1;
      parsed.push({
        id: generateStableId("p", currentParagraph, idx),
        type: "paragraph",
        content: currentParagraph.trim()
      });
      currentParagraph = "";
    }
  };
  
  for (let line of lines) {
    line = line.trim();
    if (line.startsWith("<!DOCTYPE") || line.startsWith("<html") || line.startsWith("<head") || line.startsWith("<meta") || line.startsWith("<link") || line.startsWith("<script") || line.startsWith("</head") || line.startsWith("</html") || line.startsWith("</body>") || line.startsWith("</html>")) {
      continue;
    }
    if (line.includes("<div className=\"paper-title\"") || line.includes("<div class=\"paper-title\"")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").trim();
      parsed.push({ id: "title", type: "title", content: text });
      continue;
    }
    if (line.includes("<div className=\"author-name\"") || line.includes("<div class=\"author-name\"") || line.includes("<div className=\"author-block\"") || line.includes("<div class=\"author-block\"")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").trim();
      parsed.push({ id: "authors", type: "authors", content: text });
      continue;
    }
    if (line.includes("<div className=\"author-affiliation\"") || line.includes("<div class=\"author-affiliation\"")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").trim();
      idx += 1;
      parsed.push({ id: generateStableId("aff", text, idx), type: "affiliation", content: text });
      continue;
    }
    if (line.includes("<div className=\"abstract-text\"") || line.includes("<div class=\"abstract-text\"") || line.includes("Abstract</div>")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").replace("Abstract", "").trim();
      parsed.push({ id: "abstract", type: "abstract", content: text });
      continue;
    }
    if (line.includes("<div className=\"keywords\"") || line.includes("<div class=\"keywords\"") || line.includes("Keywords—")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").trim();
      parsed.push({ id: "keywords", type: "keywords", content: text });
      continue;
    }
    if (line.startsWith("<h2") || line.startsWith("## ")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").replace("## ", "").trim();
      idx += 1;
      parsed.push({ id: generateStableId("h", text, idx), type: "heading", content: text });
      continue;
    }
    if (line.startsWith("<h3") || line.startsWith("### ")) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").replace("### ", "").trim();
      idx += 1;
      parsed.push({ id: generateStableId("sub", text, idx), type: "subheading", content: text });
      continue;
    }
    if (line.startsWith("<li>") || line.match(/^\[\d+\]/)) {
      flushParagraph();
      const text = line.replace(/<[^>]+>/g, "").trim();
      idx += 1;
      parsed.push({ id: generateStableId("ref", text, idx), type: "references", content: text });
      continue;
    }
    if (line === "") {
      flushParagraph();
    } else {
      currentParagraph += (currentParagraph ? " " : "") + line;
    }
  }
  flushParagraph();
  return parsed;
}

function getInitialBlocks(paper: Paper | null | undefined, markdown: string): Block[] {
  if (paper) {
    const initialBlocks: Block[] = [];
    initialBlocks.push({ id: "title", type: "title", content: paper.title || "" });
    
    const authors = Array.isArray(paper.authors) ? paper.authors.join(", ") : (paper.authors || "");
    initialBlocks.push({ id: "authors", type: "authors", content: authors });
    
    if (paper.abstract) {
      initialBlocks.push({ id: "abstract", type: "abstract", content: paper.abstract });
    }
    
    const keywords = Array.isArray(paper.keywords) ? paper.keywords.join(", ") : (paper.keywords || "");
    if (keywords) {
      initialBlocks.push({ id: "keywords", type: "keywords", content: keywords });
    }
    
    if (Array.isArray(paper.sections)) {
      let sectIdx = 0;
      paper.sections.forEach((sec: PaperSection) => {
        sectIdx += 1;
        initialBlocks.push({ id: `h-${sectIdx}`, type: "heading", content: sec.heading });
        if (sec.content) {
          sectIdx += 1;
          initialBlocks.push({ id: `p-${sectIdx}`, type: "paragraph", content: sec.content });
        }
        if (Array.isArray(sec.subsections)) {
          sec.subsections.forEach((sub: PaperSection) => {
            sectIdx += 1;
            initialBlocks.push({ id: `sub-${sectIdx}`, type: "subheading", content: sub.heading });
            if (sub.content) {
              sectIdx += 1;
              initialBlocks.push({ id: `p-${sectIdx}`, type: "paragraph", content: sub.content });
            }
          });
        }
      });
    }
    
    if (Array.isArray(paper.references) && paper.references.length > 0) {
      initialBlocks.push({ id: "ref-heading", type: "heading", content: "References" });
      let refIdx = 0;
      paper.references.forEach((ref: string) => {
        refIdx += 1;
        initialBlocks.push({ id: `ref-${refIdx}`, type: "references", content: ref });
      });
    }
    return initialBlocks;
  } else if (markdown) {
    return parseMarkdownToBlocks(markdown);
  }
  return [];
}


export function PaperViewer({ markdown, title, paper }: PaperViewerProps) {
  const store = useResearchStore();
  const [copied, setCopied] = useState(false);
  const [blocks, setBlocks] = useState<Block[]>(() => getInitialBlocks(paper, markdown));
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [showInsertMenu, setShowInsertMenu] = useState<number | null>(null);
  const visualIdCounterRef = useRef(0);
  
  // PDF Rendering States
  const [viewMode, setViewMode] = useState<"pdf" | "editor">("pdf");
  const [zoom, setZoom] = useState(100);
  const [showValidationPop, setShowValidationPop] = useState(false);

  // Prop adjustments during render phase
  const [prevPaper, setPrevPaper] = useState(paper);
  const [prevMarkdown, setPrevMarkdown] = useState(markdown);
  const [prevStoreLayout, setPrevStoreLayout] = useState(store.layout);
  const [prevStoreFont, setPrevStoreFont] = useState(store.font);

  if (paper !== prevPaper || markdown !== prevMarkdown) {
    setPrevPaper(paper);
    setPrevMarkdown(markdown);
    setBlocks(getInitialBlocks(paper, markdown));
  }

  // Layout & Font states linked to store defaults
  const [layoutType, setLayoutType] = useState<LayoutType>("2 Column");
  const [fontFamily, setFontFamily] = useState("Times New Roman");
  const [customFontInput, setCustomFontInput] = useState("");
  const [showCustomFontText, setShowCustomFontText] = useState(false);

  // Tooltip details for interactive visualizations
  const [activeTooltip, setActiveTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  if (store.layout !== prevStoreLayout) {
    setPrevStoreLayout(store.layout);
    if (store.layout) setLayoutType(store.layout);
  }

  if (store.font !== prevStoreFont) {
    setPrevStoreFont(store.font);
    if (store.font) {
      const standardFonts = ["Times New Roman", "Cambria", "Georgia", "Arial", "Calibri"];
      if (standardFonts.includes(store.font)) {
        setFontFamily(store.font);
      } else {
        setFontFamily("Custom");
        setCustomFontInput(store.font);
        setShowCustomFontText(true);
      }
    }
  }

  const blocksToPaperData = (currentBlocks: Block[]): EditablePaperData => {
    const titleBlock = currentBlocks.find(b => b.type === "title");
    const authorsBlock = currentBlocks.find(b => b.type === "authors");
    const abstractBlock = currentBlocks.find(b => b.type === "abstract");
    const keywordsBlock = currentBlocks.find(b => b.type === "keywords");
    
    const sections: EditablePaperSection[] = [];
    let currentSection: EditablePaperSection | null = null;
    let currentSubsection: EditablePaperSection | null = null;
    
    currentBlocks.forEach(b => {
      if (b.type === "heading") {
        if (b.content.toLowerCase() === "references") return;
        currentSection = {
          heading: b.content,
          content: "",
          subsections: []
        };
        sections.push(currentSection);
        currentSubsection = null;
      } else if (b.type === "subheading") {
        if (currentSection) {
          currentSubsection = {
            heading: b.content,
            content: "",
            subsections: []
          };
          currentSection.subsections.push(currentSubsection);
        }
      } else if (b.type === "paragraph") {
        if (currentSubsection) {
          currentSubsection.content += (currentSubsection.content ? "\n" : "") + b.content;
        } else if (currentSection) {
          currentSection.content += (currentSection.content ? "\n" : "") + b.content;
        }
      } else if (b.type === "visual") {
        let visualText = "";
        if (b.visualType === "image") {
          visualText = `\n![${b.caption}](converter_prototype_testbed.png)\n`;
        } else if (b.visualType === "heatmap") {
          visualText = `\n![${b.caption}](heatmap)\n`;
        } else if (b.visualType === "graph") {
          visualText = `\n![${b.caption}](graph)\n`;
        } else if (b.visualType === "diagram") {
          visualText = `\n![${b.caption}](diagram)\n`;
        } else if (b.visualType === "visualization") {
          visualText = `\n![${b.caption}](visualization)\n`;
        } else {
          visualText = `\n![${b.caption}](upload)\n`;
        }
        
        if (currentSubsection) {
          currentSubsection.content += (currentSubsection.content ? "\n" : "") + visualText;
        } else if (currentSection) {
          currentSection.content += (currentSection.content ? "\n" : "") + visualText;
        }
      }
    });
    
    const references = currentBlocks.filter(b => b.type === "references").map(b => b.content);
    
    return {
      title: titleBlock?.content || "Untitled Paper",
      authors: authorsBlock?.content.split(",").map(a => a.trim()) || ["ResearchOS Autonomous System"],
      abstract: abstractBlock?.content || "",
      keywords: keywordsBlock?.content.replace("Keywords—", "").split(",").map(k => k.trim()) || [],
      sections,
      references,
      layout: layoutType,
      font: fontFamily === "Custom" ? customFontInput : fontFamily
    };
  };

  const handleCopy = async () => {
    const textRepr = blocks.map(b => {
      if (b.type === "title") return `# ${b.content}\n`;
      if (b.type === "heading") return `\n## ${b.content}\n`;
      if (b.type === "subheading") return `\n### ${b.content}\n`;
      if (b.type === "visual") return `\n[Visual: ${b.visualType} - ${b.caption}]\n`;
      return b.content;
    }).join("\n");
    await navigator.clipboard.writeText(textRepr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPDF = async () => {
    if (!store.sessionId) return;
    try {
      let response;
      if (viewMode === "pdf") {
        const fontName = fontFamily === "Custom" ? customFontInput : fontFamily;
        response = await fetch(
          `${API_URL}/api/research/${store.sessionId}/pdf?layout=${encodeURIComponent(layoutType)}&font=${encodeURIComponent(fontName)}`
        );
      } else {
        const paperData = blocksToPaperData(blocks);
        response = await fetch(
          `${API_URL}/api/research/${store.sessionId}/pdf`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(paperData)
          }
        );
      }
      
      if (!response.ok) throw new Error("Failed to compile PDF");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `paper_${store.sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Error generating PDF. Please ensure the backend and Playwright dependencies are fully online.");
    }
  };

  const handleDownloadLaTeX = () => {
    const paperData = blocksToPaperData(blocks);
    
    let tex = `% IEEE Tran LaTeX Publication Document Generated by ResearchOS\n`;
    tex += `\\documentclass[journal]{IEEEtran}\n`;
    tex += `\\usepackage{cite}\n`;
    tex += `\\usepackage{amsmath,amssymb,amsfonts}\n`;
    tex += `\\usepackage{graphicx}\n`;
    tex += `\\usepackage{textcomp}\n`;
    tex += `\\usepackage{xcolor}\n\n`;
    tex += `\\begin{document}\n\n`;
    
    tex += `\\title{${paperData.title.toUpperCase()}}\n`;
    tex += `\\author{${paperData.authors.join(", ")}}\n`;
    tex += `\\maketitle\n\n`;
    
    if (paperData.abstract) {
      tex += `\\begin{abstract}\n${paperData.abstract}\n\\end{abstract}\n\n`;
    }
    if (paperData.keywords.length > 0) {
      tex += `\\begin{IEEEkeywords}\n${paperData.keywords.join(", ")}\n\\end{IEEEkeywords}\n\n`;
    }
    
    paperData.sections.forEach((sec) => {
      tex += `\\section{${sec.heading}}\n`;
      if (sec.content) {
        tex += `${sec.content}\n\n`;
      }
      sec.subsections.forEach((sub) => {
        tex += `\\subsection{${sub.heading}}\n`;
        if (sub.content) {
          tex += `${sub.content}\n\n`;
        }
      });
    });
    
    if (paperData.references.length > 0) {
      tex += `\\begin{thebibliography}{00}\n`;
      paperData.references.forEach((ref: string, idx: number) => {
        tex += `\\bibitem{b${idx + 1}} ${ref}\n`;
      });
      tex += `\\end{thebibliography}\n`;
    }
    
    tex += `\\end{document}\n`;
    
    const blob = new Blob([tex], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `paper_${store.sessionId || "document"}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadDOCX = () => {
    const paperData = blocksToPaperData(blocks);
    const htmlString = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head><title>${paperData.title}</title>
      <style>
        body { font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.25; }
        h1 { text-align: center; font-size: 24pt; font-weight: bold; color: #1e40af; margin-bottom: 12pt; text-transform: uppercase; }
        h2 { font-size: 16pt; font-weight: bold; color: #1e40af; margin-top: 18pt; margin-bottom: 6pt; border-bottom: 1px solid #1e40af; }
        h3 { font-size: 13pt; font-weight: bold; margin-top: 12pt; margin-bottom: 4pt; }
        p { text-indent: 0.25in; margin-bottom: 6pt; text-align: justify; }
        .abstract { font-style: italic; margin-bottom: 12pt; background-color: #f3f4f6; padding: 12pt; border: 1px solid #d1d5db; }
      </style>
      </head>
      <body>
        <h1>${paperData.title}</h1>
        <p style="text-align: center; font-weight: bold; text-indent: 0;">${paperData.authors.join(", ")}</p>
        <p style="text-align: center; font-style: italic; text-indent: 0; font-size: 9pt; color: #444;">ResearchOS Autonomous System</p>
        <div class="abstract">
          <strong>Abstract—</strong>${paperData.abstract}<br/><br/>
          <strong>Keywords—</strong>${paperData.keywords.join(", ")}
        </div>
        ${paperData.sections.map(s => `
          <h2>${s.heading}</h2>
          <p>${s.content.replace(/\n/g, "</p><p>")}</p>
          ${s.subsections.map((sub) => `
            <h3>${sub.heading}</h3>
            <p>${sub.content.replace(/\n/g, "</p><p>")}</p>
          `).join("")}
        `).join("")}
        <h2>References</h2>
        <ol>
          ${paperData.references.map(r => `<li>${r}</li>`).join("")}
        </ol>
      </body>
      </html>
    `;
    const blob = new Blob(['\ufeff' + htmlString], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `paper_${store.sessionId || "document"}.doc`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadMarkdown = () => {
    let textRepr = "";
    if (viewMode === "pdf" && store.markdown) {
      textRepr = store.markdown;
    } else {
      textRepr = blocks.map(b => {
        if (b.type === "title") return `# ${b.content}\n`;
        if (b.type === "heading") return `\n## ${b.content}\n`;
        if (b.type === "subheading") return `\n### ${b.content}\n`;
        if (b.type === "visual") return `\n[Visual: ${b.visualType} - ${b.caption}]\n`;
        return b.content;
      }).join("\n");
    }
    const blob = new Blob([textRepr], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Live editing block content update
  const updateBlockContent = (id: string, newContent: string) => {
    setBlocks(prev => prev.map(b => b.id === id ? { ...b, content: newContent } : b));
  };

  // Live editing visual caption update
  const updateVisualCaption = (id: string, newCaption: string) => {
    setBlocks(prev => prev.map(b => b.id === id ? { ...b, caption: newCaption } : b));
  };

  // Delete a block
  const deleteBlock = (id: string) => {
    setBlocks(prev => prev.filter(b => b.id !== id));
  };

  // Insert visual block live
  const insertVisualBlock = (index: number, visualType: Block["visualType"]) => {
    visualIdCounterRef.current += 1;
    const newBlock: Block = {
      id: `visual-${visualType}-${index}-${visualIdCounterRef.current}`,
      type: "visual",
      content: "",
      visualType,
      caption: `Fig. ${blocks.filter(b => b.type === "visual").length + 1}. Live ${visualType?.toUpperCase()} visualization.`,
      metadata: visualType === "heatmap" ? {
        matrix: [
          [75, 82, 85, 78, 62, 55],
          [68, 74, 80, 85, 70, 58],
          [62, 70, 75, 79, 74, 61],
          [58, 62, 68, 74, 75, 65],
          [55, 59, 61, 68, 70, 68],
          [52, 54, 55, 60, 62, 64]
        ]
      } : {}
    };
    
    setBlocks(prev => {
      const updated = [...prev];
      updated.splice(index, 0, newBlock);
      return updated;
    });
    setShowInsertMenu(null);
  };

  const getFontFamilyStyle = () => {
    if (fontFamily === "Times New Roman") return "font-['Times_New_Roman'] font-serif";
    if (fontFamily === "Cambria") return "font-[Cambria] font-serif";
    if (fontFamily === "Georgia") return "font-[Georgia] font-serif";
    if (fontFamily === "Arial") return "font-[Arial] font-sans";
    if (fontFamily === "Calibri") return "font-[Calibri] font-sans";
    return `font-mono`; 
  };

  const updateHeatmapCell = (blockId: string, r: number, c: number, val: number) => {
    setBlocks(prev => prev.map(b => {
      if (b.id === blockId && b.metadata?.matrix) {
        const nextMatrix = [...(b.metadata.matrix as number[][]).map((row: number[]) => [...row])];
        nextMatrix[r][c] = val;
        return { ...b, metadata: { ...b.metadata, matrix: nextMatrix } };
      }
      return b;
    }));
  };

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-primary)]">
      {/* MASTER TOOLBAR */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50 backdrop-blur">
        <div className="flex items-center gap-4">
          {/* Mode Switcher */}
          <div className="flex bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-0.5 shadow-inner">
            <button
              onClick={() => setViewMode("pdf")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
                viewMode === "pdf"
                  ? "bg-[var(--color-accent)] text-white shadow-md shadow-[var(--color-accent)]/15"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              PDF Print Layout
            </button>
            <button
              onClick={() => setViewMode("editor")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
                viewMode === "editor"
                  ? "bg-[var(--color-accent)] text-white shadow-md shadow-[var(--color-accent)]/15"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" />
              Live Editor
            </button>
          </div>
          
          {/* Layout Selector */}
          <div className="flex items-center gap-1.5 border-l border-[var(--color-border)] pl-4">
            <Layout className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
            <select
              value={layoutType}
              onChange={(e) => setLayoutType(e.target.value as LayoutType)}
              className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded text-xs px-2 py-1 outline-none text-[var(--color-text-secondary)]"
            >
              <option value="1 Column">1 Column</option>
              <option value="2 Column">2 Column (IEEE Default)</option>
              <option value="Multi Column">Multi Column</option>
            </select>
          </div>

          {/* Font Selector */}
          <div className="flex items-center gap-1.5 border-l border-[var(--color-border)] pl-4">
            <Type className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
            <select
              value={fontFamily}
              onChange={(e) => {
                setFontFamily(e.target.value);
                setShowCustomFontText(e.target.value === "Custom");
              }}
              className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded text-xs px-2 py-1 outline-none text-[var(--color-text-secondary)]"
            >
              <option value="Times New Roman">Times New Roman</option>
              <option value="Cambria">Cambria</option>
              <option value="Georgia">Georgia</option>
              <option value="Arial">Arial</option>
              <option value="Calibri">Calibri</option>
              <option value="Custom">User custom font...</option>
            </select>

            {showCustomFontText && (
              <input
                type="text"
                placeholder="Font name..."
                value={customFontInput}
                onChange={(e) => setCustomFontInput(e.target.value)}
                className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded text-xs px-2 py-1 outline-none text-[var(--color-text-secondary)] w-28"
              />
            )}
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2">
          {/* Zoom controls for Editor View */}
          {viewMode === "editor" && (
            <div className="flex items-center gap-1 border-r border-[var(--color-border)] pr-2 mr-2">
              <button 
                onClick={() => setZoom(Math.max(50, zoom - 10))}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] rounded"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono text-[var(--color-text-muted)] w-10 text-center">{zoom}%</span>
              <button 
                onClick={() => setZoom(Math.min(150, zoom + 10))}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] rounded"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] rounded transition-all"
          >
            {copied ? <Check className="w-3 h-3 text-[var(--color-success)]" /> : <Copy className="w-3 h-3" />}
            Copy Text
          </button>
          
          {store.validation && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded border bg-[var(--color-bg-tertiary)] border-[var(--color-border)] text-[var(--color-text-secondary)] select-none">
              <span className="font-semibold">Topic Relevance:</span>
              <span className={`font-bold ${store.validation.topic_relevance_passed ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}`}>
                {store.validation.relevance_score}%
              </span>
            </div>
          )}

          <div className="relative">
            <button
              onClick={handleDownloadPDF}
              disabled={false}
              className="flex items-center gap-1.5 px-3 py-1 text-xs text-white rounded shadow transition-all bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]"
              title="Download typeset PDF publication"
              onMouseEnter={() => store.validation && !store.validation.validation_passed && setShowValidationPop(true)}
              onMouseLeave={() => setShowValidationPop(false)}
            >
              <Download className="w-3 h-3" />
              Download PDF
            </button>
            {showValidationPop && store.validation && (
              <div className="absolute right-0 bottom-full mb-2 w-72 p-3 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg shadow-xl z-50 text-[11px] text-[var(--color-text-secondary)] flex flex-col gap-2">
                <span className="font-bold text-[var(--color-text-primary)] border-b border-[var(--color-border)] pb-1 flex items-center justify-between">
                  <span>PDF Validation Gates</span>
                  <span className={`text-[9px] px-1.5 rounded uppercase font-bold ${store.validation.validation_passed ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}`}>
                    {store.validation.validation_passed ? "Passed" : "Locked"}
                  </span>
                </span>
                <div className="flex items-center justify-between">
                  <span>Page Count ({store.validation.actual_pages}/{store.validation.requested_pages})</span>
                  <span className={store.validation.page_count_achieved ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                    {store.validation.page_count_achieved ? "✓ Passed" : "✗ Failed"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Topic Relevance ({store.validation.relevance_score}%)</span>
                  <span className={store.validation.topic_relevance_passed ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                    {store.validation.topic_relevance_passed ? "✓ Passed (≥85%)" : "✗ Failed (<85%)"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Minimum Sources ({store.validation.actual_sources}/{store.validation.min_sources})</span>
                  <span className={store.validation.sources_met ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                    {store.validation.sources_met ? "✓ Passed" : "✗ Failed"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Citation Coverage</span>
                  <span className={store.validation.citation_coverage_passed ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                    {store.validation.citation_coverage_passed ? "✓ Passed" : "✗ Failed"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>IEEE Formatting Rules</span>
                  <span className={store.validation.ieee_formatting_passed ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                    {store.validation.ieee_formatting_passed ? "✓ Passed" : "✗ Failed"}
                  </span>
                </div>
                {!store.validation.validation_passed && (
                  <p className="text-[10px] text-red-400 mt-1 italic border-t border-[var(--color-border)] pt-1.5">
                    * ResearchOS enforces 100% compliance. All gates must pass before PDF download is enabled.
                  </p>
                )}
              </div>
            )}
          </div>

          <button
            onClick={handleDownloadLaTeX}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] rounded transition-all"
          >
            <FileCode className="w-3 h-3 text-indigo-400" />
            LaTeX
          </button>

          <button
            onClick={handleDownloadDOCX}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] rounded transition-all"
          >
            <Download className="w-3 h-3 text-blue-400" />
            Word
          </button>

          <button
            onClick={handleDownloadMarkdown}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] rounded transition-all"
          >
            <Download className="w-3 h-3 text-emerald-400" />
            Markdown
          </button>
        </div>
      </div>

      {/* VIEWER WORKSPACE */}
      <div className="flex-1 overflow-y-auto p-4 flex justify-center bg-[var(--color-bg-secondary)]/15 min-h-0">
        <AnimatePresence mode="wait">
          {viewMode === "pdf" ? (
            <motion.div
              key="pdf-view"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.2 }}
              className="w-full h-full max-w-5xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl overflow-hidden shadow-2xl relative"
            >
              {store.sessionId ? (
                <iframe
                  key={`${store.sessionId}-${layoutType}-${fontFamily}-${customFontInput}`}
                  src={`${API_URL}/api/research/${store.sessionId}/preview?layout=${encodeURIComponent(layoutType)}&font=${encodeURIComponent(fontFamily === "Custom" ? customFontInput : fontFamily)}`}
                  sandbox=""
                  className="w-full h-full border-none bg-white"
                  title="PDF Publication Preview"
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-[var(--color-text-muted)] text-sm">
                  <div className="w-10 h-10 border-2 border-[var(--color-accent)]/30 border-t-[var(--color-accent)] rounded-full animate-spin mb-4" />
                  Compiling Academic Typesetting PDF...
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="editor-view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              className="w-full flex justify-center overflow-x-auto p-4"
              style={{ contentVisibility: "auto" }}
            >
              <div 
                className={`bg-white text-black shadow-[0_12px_40px_rgba(0,0,0,0.4)] border border-gray-200 p-16 select-text transition-all duration-200 ${getFontFamilyStyle()}`}
                style={{ 
                  fontFamily: fontFamily === "Custom" && customFontInput ? customFontInput : undefined,
                  width: "8.5in",
                  minHeight: "11in",
                  transform: `scale(${zoom / 100})`,
                  transformOrigin: 'top center'
                }}
              >
                {blocks.map((block, idx) => {
                  const isTitle = block.type === "title";
                  const isAuthors = block.type === "authors";
                  const isAffiliation = block.type === "affiliation";
                  const isAbstract = block.type === "abstract";
                  const isKeywords = block.type === "keywords";
                  const isHeading = block.type === "heading";
                  const isSubheading = block.type === "subheading";
                  const isReferences = block.type === "references";
                  const isParagraph = block.type === "paragraph";
                  const isVisual = block.type === "visual";

                  const showTwoColumnLayout = (layoutType === "2 Column" || layoutType === "Multi Column") && 
                                             !isTitle && !isAuthors && !isAffiliation && !isAbstract && !isKeywords;

                  return (
                    <div 
                      key={block.id}
                      onMouseEnter={() => setHoveredIndex(idx)}
                      onMouseLeave={() => setHoveredIndex(null)}
                      className="relative group/block"
                    >
                      {/* Plus Insert Trigger */}
                      {hoveredIndex === idx && (
                        <div className="absolute -top-3 left-0 right-0 z-20 flex items-center justify-center">
                          <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-[var(--color-accent)]/30 to-transparent absolute" />
                          <button
                            onClick={() => setShowInsertMenu(showInsertMenu === idx ? null : idx)}
                            className="w-6 h-6 rounded-full bg-[var(--color-bg-tertiary)] border border-[var(--color-accent)]/50 hover:border-[var(--color-accent)] flex items-center justify-center text-[var(--color-accent)] shadow-lg hover:scale-110 transition-transform focus:outline-none"
                          >
                            <Plus className="w-3.5 h-3.5" />
                          </button>
                          
                          <AnimatePresence>
                            {showInsertMenu === idx && (
                              <motion.div
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                className="absolute top-7 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] p-2.5 rounded-xl shadow-2xl flex flex-col gap-1 z-30 w-48 text-left"
                              >
                                <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider px-2 py-1">Insert Live Visual</div>
                                <button onClick={() => insertVisualBlock(idx, "image")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><ImageIcon className="w-3.5 h-3.5 text-blue-500" /> Image File</button>
                                <button onClick={() => insertVisualBlock(idx, "graph")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><BarChart3 className="w-3.5 h-3.5 text-indigo-500" /> Efficiency Curve</button>
                                <button onClick={() => insertVisualBlock(idx, "heatmap")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><Grid className="w-3.5 h-3.5 text-red-500" /> Thermal Heatmap</button>
                                <button onClick={() => insertVisualBlock(idx, "diagram")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><Network className="w-3.5 h-3.5 text-emerald-500" /> ANFIS Network Diagram</button>
                                <button onClick={() => insertVisualBlock(idx, "upload")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><Upload className="w-3.5 h-3.5 text-amber-500" /> Upload File Screenshot</button>
                                <button onClick={() => insertVisualBlock(idx, "visualization")} className="flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-[var(--color-bg-hover)] text-xs text-[var(--color-text-secondary)] text-left w-full"><Sparkles className="w-3.5 h-3.5 text-purple-500" /> Statistical Comparison</button>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      )}

                      {/* Trash Button */}
                      {hoveredIndex === idx && !isTitle && !isAbstract && (
                        <button
                          onClick={() => deleteBlock(block.id)}
                          className="absolute -right-8 top-1/2 -translate-y-1/2 text-red-600 hover:text-red-800 p-1.5 rounded bg-gray-100 border border-gray-300 z-10 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {/* Layout Container */}
                      <div className={`${showTwoColumnLayout ? (layoutType === "Multi Column" ? "w-1/3 float-left pr-4" : "w-1/2 float-left pr-4") : "w-full"}`}>
                        
                        {/* TITLE */}
                        {isTitle && (
                          <h1 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[22pt] font-bold text-center text-[#1e40af] mb-4 uppercase tracking-tight focus:outline-none focus:bg-blue-50 p-1 rounded"
                          >
                            {block.content}
                          </h1>
                        )}

                        {/* AUTHORS */}
                        {isAuthors && (
                          <div 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[11pt] font-bold text-center text-gray-800 mb-1 focus:outline-none"
                          >
                            {block.content}
                          </div>
                        )}

                        {/* AFFILIATION */}
                        {isAffiliation && (
                          <div 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[9pt] text-center text-gray-600 italic mb-4 focus:outline-none"
                          >
                            {block.content}
                          </div>
                        )}

                        {/* ABSTRACT BOX */}
                        {isAbstract && (
                          <div className="border border-gray-300 p-4 bg-gray-50 rounded mb-4 text-justify">
                            <span className="font-bold italic text-[#1e40af] text-[10pt] uppercase tracking-wider block mb-1">Abstract</span>
                            <div 
                              contentEditable
                              suppressContentEditableWarning
                              onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                              className="text-[9.5pt] italic text-gray-800 leading-relaxed focus:outline-none"
                            >
                              {block.content}
                            </div>
                          </div>
                        )}

                        {/* KEYWORDS */}
                        {isKeywords && (
                          <div className="text-[9pt] text-gray-800 mb-6 text-justify">
                            <span className="font-bold italic text-gray-900">Keywords—</span>
                            <span 
                              contentEditable
                              suppressContentEditableWarning
                              onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                              className="focus:outline-none"
                            >
                              {block.content.replace(/^Keywords—\s*/, "")}
                            </span>
                          </div>
                        )}

                        {/* HEADINGS */}
                        {isHeading && (
                          <h2 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[15pt] font-bold text-center text-[#1e40af] uppercase mt-6 mb-2 border-b border-gray-100 pb-1 focus:outline-none"
                          >
                            {block.content}
                          </h2>
                        )}

                        {/* SUBHEADINGS */}
                        {isSubheading && (
                          <h3 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[12pt] font-bold text-gray-900 mt-4 mb-2 focus:outline-none"
                          >
                            {block.content}
                          </h3>
                        )}

                        {/* PARAGRAPH TEXT */}
                        {isParagraph && (
                          <p 
                            contentEditable
                            suppressContentEditableWarning
                            onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                            className="text-[10pt] leading-relaxed text-gray-800 text-justify mb-3 focus:outline-none indent-6"
                          >
                            {block.content}
                          </p>
                        )}

                        {/* REFERENCES */}
                        {isReferences && (
                          <div className="flex gap-2 text-[8.5pt] text-gray-700 mb-2 text-justify font-serif">
                            <span 
                              contentEditable
                              suppressContentEditableWarning
                              onBlur={(e) => updateBlockContent(block.id, e.target.innerText)}
                              className="focus:outline-none pl-4 indent-[-16px] leading-snug"
                            >
                              {block.content}
                            </span>
                          </div>
                        )}

                        {/* LIVE VISUALS */}
                        {isVisual && (
                          <div className="my-6 border border-gray-200 rounded-lg p-4 bg-gray-50 flex flex-col items-center justify-center gap-3">
                            {block.visualType === "graph" && (
                              <div className="w-full max-w-sm flex flex-col items-center">
                                <svg className="w-full h-44 bg-gray-900 rounded-lg border border-gray-800 shadow-inner" viewBox="0 0 400 200">
                                  <g className="stroke-gray-800" strokeWidth="0.5" />
                                  <line x1="40" y1="20" x2="40" y2="170" stroke="#888" strokeWidth="1" />
                                  <line x1="40" y1="170" x2="380" y2="170" stroke="#888" strokeWidth="1" />
                                  
                                  <text x="30" y="25" fill="#888" fontSize="8" textAnchor="end">100</text>
                                  <text x="30" y="60" fill="#888" fontSize="8" textAnchor="end">95</text>
                                  <text x="30" y="95" fill="#888" fontSize="8" textAnchor="end">90</text>
                                  <text x="30" y="130" fill="#888" fontSize="8" textAnchor="end">85</text>
                                  <text x="30" y="165" fill="#888" fontSize="8" textAnchor="end">80</text>
                                  
                                  <text x="40" y="182" fill="#888" fontSize="8" textAnchor="middle">0</text>
                                  <text x="125" y="182" fill="#888" fontSize="8" textAnchor="middle">5</text>
                                  <text x="210" y="182" fill="#888" fontSize="8" textAnchor="middle">10</text>
                                  <text x="295" y="182" fill="#888" fontSize="8" textAnchor="middle">15</text>
                                  <text x="380" y="182" fill="#888" fontSize="8" textAnchor="middle">20</text>
                                  
                                  <text x="210" y="194" fill="#888" fontSize="8" textAnchor="middle">Output Current (A)</text>
                                  <text x="12" y="90" fill="#888" fontSize="8" transform="rotate(-90 12 90)" textAnchor="middle">Efficiency (%)</text>
                                  
                                  <path d="M 40 140 Q 150 50 380 90" fill="none" stroke="#eab308" strokeWidth="1.5" strokeDasharray="2" />
                                  <path d="M 40 120 Q 150 30 380 50" fill="none" stroke="#22c55e" strokeWidth="1.5" />
                                  <path d="M 40 100 Q 150 15 380 20" fill="none" stroke="#3b82f6" strokeWidth="2.5" />
                                  
                                  <circle cx="210" cy="30" r="4" fill="#3b82f6" className="cursor-pointer hover:scale-150 transition-transform" 
                                    onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY - 40, text: "Proposed ANFIS: 98.4% Efficiency @ 10A" })}
                                    onMouseLeave={() => setActiveTooltip(null)}
                                  />
                                  <circle cx="210" cy="52" r="4" fill="#22c55e" className="cursor-pointer hover:scale-150 transition-transform" 
                                    onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY - 40, text: "Fuzzy Logic: 94.2% Efficiency @ 10A" })}
                                    onMouseLeave={() => setActiveTooltip(null)}
                                  />
                                  <circle cx="210" cy="74" r="4" fill="#eab308" className="cursor-pointer hover:scale-150 transition-transform" 
                                    onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY - 40, text: "Conventional PID: 89.8% Efficiency @ 10A" })}
                                    onMouseLeave={() => setActiveTooltip(null)}
                                  />
                                  
                                  <rect x="270" y="110" width="100" height="42" fill="#000" stroke="#333" rx="3" />
                                  <line x1="275" y1="120" x2="290" y2="120" stroke="#3b82f6" strokeWidth="2" />
                                  <text x="296" y="123" fill="#eee" fontSize="7">ANFIS (Proposed)</text>
                                  <line x1="275" y1="130" x2="290" y2="130" stroke="#22c55e" strokeWidth="1.5" />
                                  <text x="296" y="133" fill="#eee" fontSize="7">Fuzzy Controller</text>
                                  <line x1="275" y1="140" x2="290" y2="140" stroke="#eab308" strokeWidth="1.5" strokeDasharray="2" />
                                  <text x="296" y="143" fill="#eee" fontSize="7">PID Controller</text>
                                </svg>
                              </div>
                            )}

                            {block.visualType === "heatmap" && (
                              <div className="flex flex-col items-center gap-2 p-2 w-full">
                                <div className="grid grid-cols-6 gap-1 w-full max-w-[260px]">
                                  {(block.metadata?.matrix as number[][])?.map((row: number[], rIdx: number) => 
                                    row.map((val: number, cIdx: number) => {
                                      const pct = Math.max(0, Math.min(100, (val - 40) / 50));
                                      const red = Math.floor(pct * 255);
                                      const blue = Math.floor((1 - pct) * 255);
                                      const green = Math.floor(pct * 40 + (1 - pct) * 40);
                                      return (
                                        <input
                                          key={`${rIdx}-${cIdx}`}
                                          type="number"
                                          value={val}
                                          onChange={(e) => updateHeatmapCell(block.id, rIdx, cIdx, Number(e.target.value))}
                                          className="w-9 h-9 border border-black/30 rounded text-[9px] font-mono text-center font-bold text-white shadow-inner focus:outline-none transition-colors"
                                          style={{ backgroundColor: `rgb(${red}, ${green}, ${blue})` }}
                                          onMouseMove={(e) => setActiveTooltip({ 
                                            x: e.clientX, 
                                            y: e.clientY - 40, 
                                            text: `Switch [${rIdx},${cIdx}]: ${val}°C (${val > 80 ? "HIGH THERMAL LOAD" : "Nominal"})` 
                                          })}
                                          onMouseLeave={() => setActiveTooltip(null)}
                                        />
                                      );
                                    })
                                  )}
                                </div>
                                <span className="text-[9px] text-gray-500 font-mono">Tip: Click values to change cell temperatures.</span>
                              </div>
                            )}

                            {block.visualType === "diagram" && (
                              <div className="w-full max-w-md h-40 relative flex items-center justify-center p-1 bg-gray-900 rounded-lg">
                                <svg className="w-full h-full" viewBox="0 0 360 160">
                                  <circle cx="40" cy="50" r="10" fill="#3b82f6" opacity="0.8" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Input 1 [Error e(t)]: Gaussian membership node" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <circle cx="40" cy="110" r="10" fill="#3b82f6" opacity="0.8" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Input 2 [Change of Error Δe(t)]: Gaussian membership node" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <text x="40" y="53" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">e</text>
                                  <text x="40" y="113" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">Δe</text>
                                  
                                  <line x1="50" y1="50" x2="100" y2="40" stroke="#888" strokeWidth="0.75" />
                                  <line x1="50" y1="50" x2="100" y2="120" stroke="#888" strokeWidth="0.75" />
                                  <line x1="50" y1="110" x2="100" y2="40" stroke="#888" strokeWidth="0.75" />
                                  <line x1="50" y1="110" x2="100" y2="120" stroke="#888" strokeWidth="0.75" />
                                  
                                  <circle cx="110" cy="40" r="10" fill="#a855f7" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Rule Node 1: Firing strength via product aggregation" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <circle cx="110" cy="120" r="10" fill="#a855f7" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Rule Node 2: Firing strength via product aggregation" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <text x="110" y="43" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">∏</text>
                                  <text x="110" y="123" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">∏</text>
                                  
                                  <line x1="120" y1="40" x2="170" y2="80" stroke="#888" strokeWidth="0.75" />
                                  <line x1="120" y1="120" x2="170" y2="80" stroke="#888" strokeWidth="0.75" />
                                  
                                  <circle cx="180" cy="80" r="10" fill="#eab308" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Normalization Layer: Computes relative rule weights" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <text x="180" y="83" textAnchor="middle" fill="#000" fontSize="8" fontWeight="bold">N</text>
                                  
                                  <line x1="190" y1="80" x2="240" y2="50" stroke="#888" strokeWidth="0.75" />
                                  <line x1="190" y1="80" x2="240" y2="110" stroke="#888" strokeWidth="0.75" />
                                  
                                  <circle cx="250" cy="50" r="10" fill="#10b981" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Sugeno Consequent Node: Computes first-order polynomials" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <circle cx="250" cy="110" r="10" fill="#10b981" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Sugeno Consequent Node: Computes first-order polynomials" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <text x="250" y="53" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">f1</text>
                                  <text x="250" y="113" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">f2</text>
                                  
                                  <line x1="260" y1="50" x2="310" y2="80" stroke="#888" strokeWidth="0.75" />
                                  <line x1="260" y1="110" x2="310" y2="80" stroke="#888" strokeWidth="0.75" />
                                  
                                  <circle cx="320" cy="80" r="12" fill="#ec4899" className="cursor-help" onMouseMove={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY-45, text: "Summation Node: Combined defuzzified duty cycle output" })} onMouseLeave={() => setActiveTooltip(null)} />
                                  <text x="320" y="83" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">∑</text>
                                  
                                  <text x="40" y="145" fill="#aaa" fontSize="7" textAnchor="middle">Layer 1</text>
                                  <text x="110" y="145" fill="#aaa" fontSize="7" textAnchor="middle">Layer 2</text>
                                  <text x="180" y="145" fill="#aaa" fontSize="7" textAnchor="middle">Layer 3</text>
                                  <text x="250" y="145" fill="#aaa" fontSize="7" textAnchor="middle">Layer 4</text>
                                  <text x="320" y="145" fill="#aaa" fontSize="7" textAnchor="middle">Layer 5</text>
                                </svg>
                              </div>
                            )}

                            {block.visualType === "image" && (
                              <div className="w-full max-w-sm h-36 bg-gray-900 border border-gray-800 rounded-lg flex flex-col items-center justify-center text-gray-500 gap-2">
                                <ImageIcon className="w-8 h-8 opacity-45 text-blue-400" />
                                <span className="text-[10px] font-mono">converter_prototype_testbed.png</span>
                              </div>
                            )}

                            {block.visualType === "upload" && (
                              <div className="w-full max-w-sm h-36 border border-dashed border-gray-300 hover:border-[#1e40af] transition-colors rounded-lg flex flex-col items-center justify-center text-gray-500 gap-2 p-4 text-center cursor-pointer">
                                <Upload className="w-8 h-8 opacity-45" />
                                <div>
                                  <span className="text-[10px] font-semibold block">Drag & Drop visual file here</span>
                                  <span className="text-[9px] text-gray-400 block mt-0.5">Supports PDF figures, SVG, PNG, JPG, CSV up to 10MB</span>
                                </div>
                              </div>
                            )}

                            {block.visualType === "visualization" && (
                              <div className="w-full max-w-sm flex flex-col gap-2 p-2">
                                <div className="flex flex-col gap-1">
                                  <div className="text-[9px] text-gray-600 font-mono flex justify-between"><span>Proposed ANFIS Control</span><span className="font-bold text-emerald-600">5.4 ms (settling time)</span></div>
                                  <div className="w-full h-2 bg-gray-250 rounded overflow-hidden bg-gray-200"><div className="h-full bg-emerald-500 rounded" style={{ width: "12%" }} /></div>
                                </div>
                                <div className="flex flex-col gap-1">
                                  <div className="text-[9px] text-gray-600 font-mono flex justify-between"><span>Fuzzy Logic Controller</span><span className="font-bold text-yellow-600">22.0 ms (settling time)</span></div>
                                  <div className="w-full h-2 bg-gray-250 rounded overflow-hidden bg-gray-200"><div className="h-full bg-yellow-500 rounded" style={{ width: "48%" }} /></div>
                                </div>
                                <div className="flex flex-col gap-1">
                                  <div className="text-[9px] text-gray-600 font-mono flex justify-between"><span>Conventional PID Control</span><span className="font-bold text-red-600">45.0 ms (settling time)</span></div>
                                  <div className="w-full h-2 bg-gray-250 rounded overflow-hidden bg-gray-200"><div className="h-full bg-red-500 rounded" style={{ width: "100%" }} /></div>
                                </div>
                              </div>
                            )}

                            <figcaption 
                              contentEditable
                              suppressContentEditableWarning
                              onBlur={(e) => updateVisualCaption(block.id, e.target.innerText)}
                              className="text-[9px] text-gray-600 font-semibold text-center italic mt-1.5 focus:outline-none focus:bg-blue-50 px-2 py-0.5 rounded"
                            >
                              {block.caption}
                            </figcaption>
                          </div>
                        )}

                      </div>
                    </div>
                  );
                })}
                <div className="clear-both" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Floating active tooltip */}
      {activeTooltip && (
        <div 
          className="fixed z-[100] pointer-events-none bg-black/90 border border-gray-800 text-[10px] font-mono px-2 py-1.5 rounded shadow-xl text-white backdrop-blur-sm"
          style={{ left: activeTooltip.x + 10, top: activeTooltip.y }}
        >
          {activeTooltip.text}
        </div>
      )}
    </div>
  );
}
