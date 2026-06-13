"""
Agent 10: IEEE Formatter
Converts the paper draft into IEEE-compliant format.
Enforces word count requirements and validates content length.
"""

from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import IEEEPaper
from services.page_budget import count_paper_words

import structlog

logger = structlog.get_logger()


IEEE_SYSTEM = """You are an IEEE paper formatting specialist. Convert the paper draft into proper IEEE conference/journal format.

CRITICAL: Preserve ALL content from the input. Do NOT shorten, summarize, or truncate any section.
The output must be AT LEAST as long as the input. You are FORMATTING, not summarizing.

STRICT FORMATTING RULES:
- Do NOT invent statistics, percentages, or numerical results that are not in the input.
- Do NOT generate tables with fabricated benchmark data. Only format tables that are already in the input.
- Do NOT add figure captions for figures that do not exist.
- Do NOT add author names that are not provided. Use "ResearchOS Autonomous System" as default.
- Preserve all citation keys [1], [2] exactly as they appear in the input.
- If a section has no data to support a claim, preserve the limitation statement.

Output valid JSON:
{
    "title": "Paper Title in Title Case",
    "authors": ["Author Name"],
    "abstract": "Abstract text (200-250 words)",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "sections": [
        {
            "heading": "I. INTRODUCTION",
            "content": "FULL section content — do not truncate...",
            "subsections": []
        }
    ],
    "references": [
        "[1] A. Author, \\"Title,\\" Publication, Year."
    ],
    "content_markdown": "Full paper in markdown format"
}

IEEE Format Rules:
- Title: centered, bold, 14pt equivalent
- Sections: Roman numerals (I, II, III), ALL CAPS for main headings
- Subsections: A, B, C
- Abstract: single paragraph, 200-250 words
- Keywords: 5-7 relevant terms
- References: IEEE numbered format [1], [2]
- Two-column layout described in markdown
- Equations numbered (1), (2)
- Figures and tables numbered Fig. 1, TABLE I
- PRESERVE ALL CONTENT — do not shorten any section"""


class IEEEFormatterAgent(BaseAgent):
    name = "ieee_formatter"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()

        title = input_data.get("title", "")
        abstract = input_data.get("abstract", "")
        sections = input_data.get("sections", [])
        conclusion = input_data.get("conclusion", "")
        citations = input_data.get("citations", [])
        target_word_count = input_data.get("target_word_count", 6000)
        topic = input_data.get("prompt") or title

        # Format sections for the formatter
        sections_text = ""
        for section in sections:
            sections_text += f"\n## {section.get('heading', '')}\n{section.get('content', '')}\n"
            for sub in section.get("subsections", []):
                sections_text += f"\n### {sub.get('heading', '')}\n{sub.get('content', '')}\n"

        references_text = "\n".join(
            c.get("ieee_format", c.get("title", ""))
            for c in citations[:30]
        )

        user_prompt = f"""Convert this paper draft to IEEE format.
CRITICAL: Do NOT shorten or summarize any content. Preserve ALL text.
Target word count: {target_word_count} words minimum.

Title: {title}

Abstract: {abstract}

{sections_text}

Conclusion: {conclusion}

References:
{references_text}

Format as a proper IEEE paper with all formatting conventions. PRESERVE ALL CONTENT."""

        result = await llm.complete_json(
            role=AgentRole.IEEE_FORMATTER,
            system_prompt=IEEE_SYSTEM,
            user_prompt=user_prompt,
        )

        # Build full markdown content
        content_md = self._build_markdown(result)

        paper = IEEEPaper(
            title=result.get("title", title),
            authors=result.get("authors", ["ResearchOS Autonomous System"]),
            abstract=result.get("abstract", abstract),
            keywords=result.get("keywords", []),
            sections=result.get("sections", []),
            references=result.get("references", []),
            content_markdown=content_md,
        )

        paper_dict = paper.model_dump()

        # ── Validate word count ─────────────────────────────
        word_stats = count_paper_words(paper_dict)
        body_words = word_stats["body_words"]

        logger.info(
            "ieee_formatter_word_count",
            body_words=body_words,
            target_words=target_word_count,
            sections=len(paper_dict.get("sections", [])),
        )

        if body_words < target_word_count * 0.5:
            # Formatter severely truncated — use original sections instead
            logger.warning(
                "ieee_formatter_truncated_using_original",
                formatted_words=body_words,
                target=target_word_count,
            )
            # Preserve original sections with IEEE headings
            ieee_sections = []
            roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
            for idx, section in enumerate(sections):
                heading = section.get("heading", "")
                # Add roman numeral if not present
                if not any(heading.upper().startswith(f"{r}.") for r in roman_numerals):
                    r_num = roman_numerals[idx] if idx < len(roman_numerals) else str(idx + 1)
                    heading = f"{r_num}. {heading.upper()}"
                ieee_sections.append({
                    "heading": heading,
                    "content": section.get("content", ""),
                    "subsections": section.get("subsections", []),
                })

            # Add conclusion as final section
            if conclusion:
                r_num = roman_numerals[len(ieee_sections)] if len(ieee_sections) < len(roman_numerals) else str(len(ieee_sections) + 1)
                ieee_sections.append({
                    "heading": f"{r_num}. CONCLUSION",
                    "content": conclusion,
                    "subsections": [],
                })

            paper_dict["sections"] = ieee_sections

        # Enforce hard topic lock on formatted output
        from services.relevance_checker import ensure_paragraph_relevance

        async def clean_text(text: str) -> str:
            if not text:
                return ""
            paragraphs = text.split("\n\n")
            cleaned_paragraphs = []
            for p in paragraphs:
                if p.strip():
                    cleaned_p = await ensure_paragraph_relevance(p, topic)
                    cleaned_paragraphs.append(cleaned_p)
                else:
                    cleaned_paragraphs.append(p)
            return "\n\n".join(cleaned_paragraphs)

        paper_dict["abstract"] = await clean_text(paper_dict.get("abstract", ""))
        for sec in paper_dict.get("sections", []):
            sec["content"] = await clean_text(sec.get("content", ""))
            for sub in sec.get("subsections", []):
                sub["content"] = await clean_text(sub.get("content", ""))

        paper_dict["content_markdown"] = self._build_markdown(paper_dict)

        return paper_dict

    def _build_markdown(self, paper_data: dict) -> str:
        """Build a complete markdown representation."""
        lines = []
        title = paper_data.get("title", "Research Paper")
        authors = ", ".join(paper_data.get("authors", ["ResearchOS"]))

        lines.append(f"# {title}")
        lines.append(f"\n*{authors}*\n")

        # Abstract
        lines.append("## Abstract")
        lines.append(paper_data.get("abstract", ""))
        lines.append("")

        # Keywords
        keywords = paper_data.get("keywords", [])
        if keywords:
            lines.append(f"**Keywords:** {', '.join(keywords)}")
            lines.append("")

        # Sections
        for section in paper_data.get("sections", []):
            lines.append(f"## {section.get('heading', '')}")
            lines.append(section.get("content", ""))
            lines.append("")
            for sub in section.get("subsections", []):
                lines.append(f"### {sub.get('heading', '')}")
                lines.append(sub.get("content", ""))
                lines.append("")

        # References
        refs = paper_data.get("references", [])
        if refs:
            lines.append("## REFERENCES")
            lines.append("")
            for ref in refs:
                lines.append(f"{ref}")
            lines.append("")

        return "\n".join(lines)
