"""
ResearchOS Publication-Grade Typesetting Engine
Generates publication-quality PDFs from structured paper models.
Primary: Playwright (Chromium). Fallback: WeasyPrint, then fpdf2.
Retries with exponential backoff via tenacity.
"""

import asyncio
import os
import re
import subprocess
import sys
import tempfile
from html import escape

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# ── Fallback renderer availability ─────────────────────
_HAS_FPDF2: bool = False

try:
    from fpdf import FPDF  # noqa: F401

    _HAS_FPDF2 = True
except ImportError:
    pass

# ── Locally bundled KaTeX (offline rendering) ────────────────────────
_KATEX_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "katex")


def _load_katex() -> tuple[str, str, str]:
    css_path = os.path.join(_KATEX_DIR, "katex.min.css")
    js_path = os.path.join(_KATEX_DIR, "katex.min.js")
    auto_path = os.path.join(_KATEX_DIR, "auto-render.min.js")
    css = ""
    js = ""
    auto = ""
    try:
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
    except FileNotFoundError:
        logger.warning("katex_css_not_found", path=css_path)
    try:
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
    except FileNotFoundError:
        logger.warning("katex_js_not_found", path=js_path)
    try:
        with open(auto_path, encoding="utf-8") as f:
            auto = f.read()
    except FileNotFoundError:
        logger.warning("katex_auto_render_not_found", path=auto_path)
    if not css:
        css = ".katex { font-size: 1.1em; } .katex-display { display: block; margin: 0.5em 0; }"
    if not js or not auto:
        js = ""
        auto = ""
    return css, js, auto


KATEX_CSS_INLINE, KATEX_JS_INLINE, KATEX_AUTO_INLINE = _load_katex()
_KATEX_OK = bool(KATEX_JS_INLINE and KATEX_AUTO_INLINE and KATEX_CSS_INLINE)

# ── Master HTML Template ─────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    {katex_css_inline}

    @page {{
      size: letter;
      margin: 0.75in 0.625in 1.0in 0.625in;

      @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        font-family: {font_css}, Times, serif;
        color: #666;
      }}
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: {font_css}, Times, serif;
      font-size: 10pt;
      line-height: 1.25;
      color: #000;
      background: #fff;
      padding: 0;
      counter-reset: figure-counter table-counter equation-counter;
    }}

    /* ── Title Block ────────────────────────── */
    .title-container {{
      text-align: center;
      margin-bottom: 14pt;
      width: 100%;
    }}

    .paper-title {{
      font-size: 22pt;
      font-weight: bold;
      color: #1a3a7a;
      margin-bottom: 10pt;
      line-height: 1.15;
      text-transform: uppercase;
      letter-spacing: -0.3pt;
    }}

    .authors-list {{
      font-size: 11pt;
      font-weight: bold;
      margin-bottom: 3pt;
      color: #111;
    }}

    .author-affiliation {{
      font-size: 9pt;
      font-style: italic;
      color: #4b5563;
      margin-bottom: 4pt;
      line-height: 1.35;
    }}

    .author-email {{
      font-size: 8.5pt;
      color: #2563eb;
      margin-bottom: 12pt;
    }}

    /* ── Abstract ────────────────────────── */
    .abstract-keywords-container {{
      width: 100%;
      margin-bottom: 12pt;
      border: none;
      padding: 0;
    }}

    .abstract-label {{
      display: none;
    }}

    .abstract-text {{
      display: inline;
    }}

    .keywords-block {{
      display: block;
      margin-top: 4pt;
    }}


    /* ── Column Layout ────────────────────────── */
    .content-flow {{
      column-count: {column_count};
      column-gap: 0.25in;
      column-fill: balance;
      text-align: justify;
      column-rule: 0.5pt solid #e8e8e8;
      min-height: 200px;
      overflow: visible;
    }}

    /* ── SVG Figures (Auto-Generated) ────────────── */
    .figure-container svg {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 6pt auto;
    }}

    /* ── Section Headings ────────────────────────── */
    .section-heading {{
      font-size: 11pt;
      font-weight: bold;
      color: #1a3a7a;
      text-align: center;
      text-transform: uppercase;
      margin: 12pt 0 6pt 0;
      break-after: avoid;
      column-span: none;
      letter-spacing: 0.3pt;
    }}

    .subsection-heading {{
      font-size: 10pt;
      font-weight: bold;
      color: #222;
      margin: 8pt 0 4pt 0;
      break-after: avoid;
      font-style: italic;
    }}

    /* ── Paragraphs ────────────────────────── */
    p {{
      text-indent: 0.2in;
      margin-bottom: 3pt;
      text-align: justify;
      line-height: 1.25;
      font-size: 10pt;
      orphans: 3;
      widows: 3;
    }}

    p.no-indent {{
      text-indent: 0;
    }}

    /* ── Tables ────────────────────────── */
    .table-container {{
      width: 100%;
      margin: 10pt 0;
      break-inside: avoid;
      text-align: center;
    }}

    .table-caption {{
      font-size: 8.5pt;
      font-weight: bold;
      text-transform: uppercase;
      margin-bottom: 4pt;
      color: #1a3a7a;
      text-align: center;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 8.5pt;
      margin: 0 auto;
    }}

    th {{
      border-top: 1.5pt solid #000;
      border-bottom: 0.75pt solid #000;
      padding: 3pt 4pt;
      font-weight: bold;
      background-color: #f5f7fa;
      text-align: center;
    }}

    td {{
      border-bottom: 0.5pt solid #d1d5db;
      padding: 2.5pt 4pt;
      text-align: center;
    }}

    tr:last-child td {{
      border-bottom: 1.5pt solid #000;
    }}

    /* ── Figures ────────────────────────── */
    .figure-container {{
      width: 100%;
      margin: 10pt 0;
      break-inside: avoid;
      text-align: center;
    }}

    .figure-caption {{
      font-size: 8.5pt;
      font-weight: normal;
      margin-top: 4pt;
      color: #333;
      text-align: center;
      font-style: normal;
    }}

    .figure-caption strong {{
      font-weight: bold;
    }}

    /* ── Equations ────────────────────────── */
    .equation-container {{
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 8pt 0;
      width: 100%;
      break-inside: avoid;
    }}

    .equation-math {{
      flex-grow: 1;
      text-align: center;
    }}

    .equation-number {{
      font-size: 10pt;
      padding-left: 8px;
      min-width: 30px;
      text-align: right;
    }}

    /* ── References ────────────────────────── */
    .references-section {{
      margin-top: 14pt;
      break-before: auto;
    }}

    .references-heading {{
      font-size: 11pt;
      font-weight: bold;
      text-transform: uppercase;
      text-align: center;
      color: #1a3a7a;
      margin-bottom: 6pt;
      letter-spacing: 0.3pt;
    }}

    .references-list {{
      list-style: none;
      padding-left: 0;
    }}

    .reference-item {{
      font-size: 8pt;
      line-height: 1.3;
      margin-bottom: 2pt;
      text-indent: -0.2in;
      padding-left: 0.2in;
      text-align: justify;
      color: #222;
    }}

    /* ── Misc ────────────────────────── */
    strong {{
      font-weight: bold;
    }}

    em {{
      font-style: italic;
    }}

    .column-break {{
      break-before: column;
    }}

    @media print {{
      body {{
        background: #fff;
      }}
    }}
  </style>
  <script>{katex_js_inline}</script>
  <script>{katex_auto_inline}</script>
</head>
<body>

  <div class="title-container">
    <h1 class="paper-title">{title}</h1>
    <div class="authors-list">{authors}</div>
    <div class="author-affiliation">{affiliation}</div>
    {email_html}
  </div>

  <div class="content-flow">
    <div class="abstract-keywords-container">
      <p class="no-indent" style="font-size: 9pt; line-height: 1.3; margin-bottom: 6pt; text-align: justify;">
        <strong><em>Abstract</em>&mdash;{abstract}</strong>
      </p>
      <p class="no-indent" style="font-size: 9pt; line-height: 1.3; margin-bottom: 12pt; text-align: justify;">
        <strong><em>Index Terms</em>&mdash;{keywords}</strong>
      </p>
    </div>

    {content_html}

    <div class="references-section">
      <h2 class="references-heading">References</h2>
      <ul class="references-list">
        {references_html}
      </ul>
    </div>
  </div>

  <script>
    document.addEventListener("DOMContentLoaded", function() {{
      if (typeof renderMathInElement !== 'undefined') {{
        renderMathInElement(document.body, {{
          delimiters: [
            {{left: "$$", right: "$$", display: true}},
            {{left: "$", right: "$", display: false}},
            {{left: "\\\\[", right: "\\\\]", display: true}},
            {{left: "\\\\(", right: "\\\\)", display: false}}
          ],
          throwOnError: false
        }});
      }}
    }});
  </script>

</body>
</html>
"""


def _escape_html(text: str) -> str:
    """Escape non-HTML text before inserting it into generated HTML."""
    if not text:
        return ""
    return escape(str(text), quote=True)


def _sanitize_raw_html_line(line: str) -> str:
    """Allow generated SVG/layout fragments while removing executable hooks."""
    sanitized = re.sub(r"<\s*/?\s*script\b[^>]*>", "", line, flags=re.IGNORECASE)
    sanitized = re.sub(r"\s+on[a-zA-Z]+\s*=\s*(['\"]).*?\1", "", sanitized)
    sanitized = re.sub(r"\s+on[a-zA-Z]+\s*=\s*[^\s>]+", "", sanitized)
    sanitized = re.sub(r"javascript\s*:", "", sanitized, flags=re.IGNORECASE)
    return sanitized


def _font_css_from_name(font: str) -> str:
    """Return a safe CSS font-family value for supported/custom font names."""
    font_map = {
        "Times New Roman": "'Times New Roman', Times",
        "Cambria": "Cambria, Georgia, Times",
        "Georgia": "Georgia, Times",
        "Arial": "Arial, Helvetica, sans-serif",
        "Calibri": "Calibri, 'Segoe UI', sans-serif",
    }
    if font in font_map:
        return font_map[font]

    safe_font = re.sub(r"[^A-Za-z0-9 ,_-]", "", font or "").strip()
    if not safe_font:
        return font_map["Times New Roman"]
    return f"'{safe_font[:80]}', sans-serif"


def parse_markdown_to_html(md_text: str) -> str:
    """Convert structured markdown into styled academic HTML."""
    if not md_text:
        return ""

    # ── JSON Leak Sanitization ──
    # Strip leftover JSON code fences and artifacts from LLM output
    md_text = re.sub(r"```json\s*", "", md_text)
    md_text = re.sub(r"```\s*", "", md_text)
    # Remove lines that are just opening/closing braces (JSON object boundaries)
    md_text = re.sub(r"^\s*[{}]\s*$", "", md_text, flags=re.MULTILINE)
    # Remove JSON dict key patterns at the start of lines like "key":
    md_text = re.sub(r'^\s*"[a-zA-Z_]+"\s*:\s*', "", md_text, flags=re.MULTILINE)
    # Remove trailing commas at end of lines (JSON list/dict remnants)
    md_text = re.sub(r",\s*$", "", md_text, flags=re.MULTILINE)

    html_out = []
    lines = md_text.split("\n")

    in_p = False
    in_table = False
    table_rows = []

    for line in lines:
        line_stripped = line.strip()

        # Table parsing
        if line_stripped.startswith("|"):
            if in_p:
                html_out.append("</p>")
                in_p = False
            in_table = True
            table_rows.append(line_stripped)
            continue
        elif in_table:
            in_table = False
            html_out.append(render_html_table(table_rows))
            table_rows = []

        # Empty line
        if not line_stripped:
            if in_p:
                html_out.append("</p>")
                in_p = False
            continue

        # Pass through raw HTML blocks (SVG figures, divs, etc.)
        if (
            line_stripped.startswith("<div")
            or line_stripped.startswith("</div")
            or line_stripped.startswith("<svg")
            or line_stripped.startswith("</svg")
            or line_stripped.startswith("<circle")
            or line_stripped.startswith("<rect")
            or line_stripped.startswith("<line")
            or line_stripped.startswith("<text")
            or line_stripped.startswith("<path")
            or line_stripped.startswith("<polyline")
            or line_stripped.startswith("<polygon")
            or line_stripped.startswith("<defs")
            or line_stripped.startswith("</defs")
            or line_stripped.startswith("<marker")
            or line_stripped.startswith("</marker")
        ):
            if in_p:
                html_out.append("</p>")
                in_p = False
            html_out.append(_sanitize_raw_html_line(line))
            continue

        # Section headings
        if line_stripped.startswith("## "):
            if in_p:
                html_out.append("</p>")
                in_p = False
            heading = line_stripped[3:]
            html_out.append(f'<h2 class="section-heading">{_escape_html(heading)}</h2>')
            continue
        elif line_stripped.startswith("### "):
            if in_p:
                html_out.append("</p>")
                in_p = False
            heading = line_stripped[4:]
            html_out.append(f'<h3 class="subsection-heading">{_escape_html(heading)}</h3>')
            continue

        # Display equations $$...$$
        if (
            line_stripped.startswith("$$")
            and line_stripped.endswith("$$")
            and len(line_stripped) > 4
        ):
            if in_p:
                html_out.append("</p>")
                in_p = False
            eq_content = line_stripped[2:-2].strip()
            # Check for equation number
            num_match = re.search(r"\((\d+)\)\s*$", eq_content)
            eq_num = ""
            if num_match:
                eq_num = num_match.group(0)
                eq_content = eq_content[: -len(eq_num)].strip()

            html_out.append(
                f'<div class="equation-container">'
                f'  <div class="equation-math">$${eq_content}$$</div>'
                f"  {f'<div class=equation-number>{eq_num}</div>' if eq_num else ''}"
                f"</div>"
            )
            continue

        # Figures / Image embeds
        fig_match = re.match(r"^!\[(.*?)\]\((.*?)\)", line_stripped)
        if fig_match:
            if in_p:
                html_out.append("</p>")
                in_p = False
            caption = fig_match.group(1)
            img_url = fig_match.group(2)
            html_out.append(
                f'<div class="figure-container">'
                f'  <img src="{_escape_html(img_url)}" style="max-width: 95%; max-height: 220px; display: block; margin: 0 auto;" />'
                f'  <div class="figure-caption"><strong>Fig.</strong> {_escape_html(caption)}</div>'
                f"</div>"
            )
            continue

        # Paragraph text
        if not in_p:
            html_out.append("<p>")
            in_p = True

        html_line = _escape_html(line)
        html_line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_line)
        html_line = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html_line)

        html_out.append(html_line + " ")

    if in_p:
        html_out.append("</p>")

    # Close any remaining table
    if in_table and table_rows:
        html_out.append(render_html_table(table_rows))

    return "\n".join(html_out)


def render_html_table(rows: list[str]) -> str:
    """Convert Markdown table rows to an HTML table with IEEE styling."""
    html = ['<div class="table-container">', "  <table>"]

    headers = []
    body_rows = []

    for row in rows:
        cells = [c.strip() for c in row.split("|")[1:-1]]
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue
        if not headers:
            headers = cells
        else:
            body_rows.append(cells)

    html.append("    <thead>")
    html.append("      <tr>")
    for h in headers:
        html.append(f"        <th>{_escape_html(h)}</th>")
    html.append("      </tr>")
    html.append("    </thead>")

    html.append("    <tbody>")
    for r in body_rows:
        html.append("      <tr>")
        for c in r:
            safe_cell = _escape_html(c)
            # Bold the "Proposed" rows
            if "<strong>" in c or "Proposed" in c:
                html.append(f"        <td><strong>{safe_cell}</strong></td>")
            else:
                html.append(f"        <td>{safe_cell}</td>")
        html.append("      </tr>")
    html.append("    </tbody>")

    html.append("  </table>")
    html.append("</div>")
    return "\n".join(html)


def _build_sections_html(sections: list[dict], content_md: str = "") -> str:
    """Build HTML from structured sections or fallback to markdown content."""
    if sections:
        sections_md = []
        for sec in sections:
            heading = sec.get("heading", "")
            content = sec.get("content", "")
            sections_md.append(f"\n## {heading}\n{content}\n")
            for sub in sec.get("subsections", []):
                sub_heading = sub.get("heading", "")
                sub_content = sub.get("content", "")
                sections_md.append(f"\n### {sub_heading}\n{sub_content}\n")
        return parse_markdown_to_html("\n".join(sections_md))
    elif content_md:
        return parse_markdown_to_html(content_md)
    return "<p>No content available.</p>"


class PDFGenerator:
    # Path to the standalone Playwright worker script
    _WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "_pdf_worker.py")

    @staticmethod
    def _check_playwright_available() -> tuple[bool, str]:
        """Check if Playwright and Chromium are available for PDF rendering."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                executable = p.chromium.executable_path
                if not executable:
                    return False, "No Chromium executable found"
                return True, executable
        except ImportError:
            return False, "playwright package not installed"
        except Exception as e:
            return False, f"Playwright error: {e}"

    @staticmethod
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((RuntimeError, subprocess.TimeoutExpired)),
        reraise=True,
    )
    async def _render_pdf_subprocess(html_path: str, pdf_path: str) -> None:
        """Run Playwright PDF rendering in a separate subprocess (Windows-safe).

        Retries up to 2 times with exponential backoff (1s, 5s).
        """
        python_exe = sys.executable
        worker_script = PDFGenerator._WORKER_SCRIPT

        logger.info(
            "spawning_pdf_worker",
            python=python_exe,
            worker=worker_script,
            html=html_path,
            pdf=pdf_path,
        )

        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [python_exe, worker_script, "render", html_path, pdf_path],
                capture_output=True,
                text=True,
                timeout=120,
            ),
        )

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or "Unknown error in PDF worker"
            stderr_lower = error_msg.lower()
            if (
                "chromium" in stderr_lower
                or "browser" in stderr_lower
                or "executable" in stderr_lower
            ):
                raise RuntimeError(f"Chromium/browser error: {error_msg}")
            logger.error("pdf_worker_failed", returncode=proc.returncode, stderr=error_msg)
            raise RuntimeError(f"PDF worker exited with code {proc.returncode}: {error_msg}")

        logger.info("pdf_worker_completed", stdout=proc.stdout.strip()[:200])

    @staticmethod
    async def _render_pdf_fallback(html_path: str, pdf_path: str) -> None:
        """Last-resort fallback: use fpdf2 to build a PDF preserving section structure."""
        if not _HAS_FPDF2:
            raise RuntimeError("fpdf2 not installed")

        from fpdf import FPDF

        logger.warning("rendering_pdf_via_fpdf2_fallback", html=html_path, pdf=pdf_path)

        try:
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()

            loop = asyncio.get_event_loop()

            def _build():
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=20)
                pdf.add_page()
                pdf.set_font("Times", size=10)

                sections = re.split(
                    r'<h2[^>]*class="section-heading"[^>]*>(.*?)</h2>',
                    html_content,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                title_match = re.search(
                    r'<h1[^>]*class="paper-title"[^>]*>(.*?)</h1>', html_content
                )
                if title_match:
                    pdf.set_font("Times", "B", 14)
                    pdf.multi_cell(0, 8, re.sub(r"<[^>]+>", "", title_match.group(1)).strip())
                    pdf.ln(4)
                    pdf.set_font("Times", size=10)

                for i, section in enumerate(sections):
                    section_text = re.sub(r"<[^>]+>", " ", section)
                    section_text = re.sub(r"\s+", " ", section_text).strip()
                    if not section_text:
                        continue
                    if i % 2 == 1:
                        pdf.set_font("Times", "B", 11)
                        pdf.multi_cell(0, 6, section_text)
                        pdf.ln(2)
                        pdf.set_font("Times", size=10)
                    else:
                        for para in re.split(r"\s{2,}", section_text):
                            para = para.strip()[:2000]
                            if para:
                                pdf.multi_cell(0, 5, para)
                                pdf.ln(1)

                pdf.output(pdf_path)

            await loop.run_in_executor(None, _build)
            logger.info("fpdf2_fallback_completed", pdf=pdf_path)

        except Exception as e:
            logger.error("fpdf2_fallback_failed", error=str(e))
            raise RuntimeError(f"fpdf2 fallback render failed: {e}") from e

    @staticmethod
    async def render_to_pdf(html_path: str, pdf_path: str) -> None:
        """Try primary renderer, then fallback chain."""
        errors = []
        # Attempt 1: Playwright (primary, with retry)
        try:
            await PDFGenerator._render_pdf_subprocess(html_path, pdf_path)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                return
        except Exception as e:
            errors.append(("playwright", str(e)))
            logger.warning("playwright_render_failed_trying_fallback", error=str(e))

        # Attempt 2: fpdf2 (last-resort text-only fallback)
        if _HAS_FPDF2:
            try:
                await PDFGenerator._render_pdf_fallback(html_path, pdf_path)
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    return
            except Exception as e:
                errors.append(("fpdf2", str(e)))

        raise RuntimeError(f"All PDF renderers failed: {'; '.join(f'{n}: {m}' for n, m in errors)}")

    @staticmethod
    async def render_and_count_pages(html_path: str, pdf_path: str) -> int:
        """Render PDF and return page count in a single subprocess call."""
        import json as _json

        python_exe = sys.executable
        worker_script = PDFGenerator._WORKER_SCRIPT

        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [python_exe, worker_script, "render_count", html_path, pdf_path],
                capture_output=True,
                text=True,
                timeout=120,
            ),
        )

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or "Unknown error in PDF worker"
            logger.error("pdf_worker_failed", returncode=proc.returncode, stderr=error_msg)
            raise RuntimeError(f"PDF worker exited with code {proc.returncode}: {error_msg}")

        try:
            result = _json.loads(proc.stdout.strip())
            page_count = result.get("page_count", 0)
        except Exception:
            page_count = 0

        logger.info("pdf_render_count_complete", page_count=page_count)
        return page_count

    @staticmethod
    async def count_pdf_pages(pdf_path: str) -> int:
        """Count pages in an existing PDF file."""
        import json as _json

        python_exe = sys.executable
        worker_script = PDFGenerator._WORKER_SCRIPT

        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [python_exe, worker_script, "count", pdf_path],
                capture_output=True,
                text=True,
                timeout=30,
            ),
        )

        if proc.returncode != 0:
            return 0

        try:
            result = _json.loads(proc.stdout.strip())
            return result.get("page_count", 0)
        except Exception:
            return 0

    @staticmethod
    async def compile_paper_to_pdf(
        paper_data: dict, layout: str = "2 Column", font: str = "Times New Roman"
    ) -> bytes:
        """Compile structured paper data into a professional publication PDF."""
        title = _escape_html(paper_data.get("title", "Research Paper"))
        abstract = _escape_html(paper_data.get("abstract", ""))
        keywords_list = paper_data.get("keywords", [])
        keywords = (
            ", ".join(str(k) for k in keywords_list)
            if isinstance(keywords_list, list)
            else str(keywords_list)
        )
        keywords = _escape_html(keywords)
        authors_list = paper_data.get("authors", ["ResearchOS Autonomous System"])
        authors = (
            ", ".join(str(a) for a in authors_list)
            if isinstance(authors_list, list)
            else str(authors_list)
        )
        authors = _escape_html(authors)

        # Column count
        column_count = "2"
        if layout == "1 Column":
            column_count = "1"
        elif layout == "Multi Column":
            column_count = "3"

        # Font CSS
        font_family = _font_css_from_name(font)

        # Build content HTML
        sections = paper_data.get("sections", [])
        content_md = paper_data.get("content_markdown", "")

        # If content_markdown is raw HTML (from the mock), use sections instead
        if content_md and content_md.strip().startswith("<!DOCTYPE"):
            content_md = ""

        content_html = _build_sections_html(sections, content_md)

        # References
        references_html = ""
        for ref in paper_data.get("references", []):
            ref_clean = _escape_html(str(ref))
            references_html += f'<li class="reference-item">{ref_clean}</li>\n'

        # Affiliation
        affiliation = _escape_html(
            paper_data.get("affiliation", "ResearchOS Autonomous Research System")
        )

        # Email
        email = paper_data.get("email", "")
        email_html = f'<div class="author-email">{_escape_html(email)}</div>' if email else ""

        full_html = HTML_TEMPLATE.format(
            title=title,
            authors=authors,
            affiliation=affiliation,
            email_html=email_html,
            abstract=abstract,
            keywords=keywords,
            font_css=font_family,
            column_count=column_count,
            content_html=content_html,
            references_html=references_html,
            katex_css_inline=KATEX_CSS_INLINE,
            katex_js_inline=KATEX_JS_INLINE,
            katex_auto_inline=KATEX_AUTO_INLINE,
        )

        pdf_bytes = b""
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "paper.html")
            pdf_path = os.path.join(tmpdir, "paper.pdf")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(full_html)

            logger.info("rendering_pdf", html_file=html_path)

            await PDFGenerator.render_to_pdf(html_path, pdf_path)

            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

        logger.info("pdf_generated", size_bytes=len(pdf_bytes))
        return pdf_bytes

    @staticmethod
    async def compile_html_to_pdf(
        html_content: str,
    ) -> bytes:
        """Compile raw HTML content directly to PDF (for pre-built HTML papers)."""
        pdf_bytes = b""
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "paper.html")
            pdf_path = os.path.join(tmpdir, "paper.pdf")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            await PDFGenerator.render_to_pdf(html_path, pdf_path)

            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

        return pdf_bytes

    @staticmethod
    def get_renderer_status() -> dict:
        """Return availability status of all PDF renderers."""
        return {
            "playwright": {"available": True, "chromium_path": PDFGenerator._get_chromium_path()},
            "fpdf2": {"available": _HAS_FPDF2},
        }

    @staticmethod
    def _get_chromium_path() -> str | None:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                return p.chromium.executable_path
        except Exception:
            return None
