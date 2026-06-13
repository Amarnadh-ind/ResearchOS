"""
Agent 9: Writer Agent
Composes the academic paper from verified claims and evidence.
RULE-5: Claims must be traceable.

Now enforces word count budgets per section to meet page targets.
"""

from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import WriterOutput


WRITER_SYSTEM = """You are an expert academic paper writer producing FULL-LENGTH IEEE journal papers.

CRITICAL: You must write COMPREHENSIVE, DETAILED sections. Each section must meet its MINIMUM WORD COUNT.
A 12-page IEEE paper requires approximately 6000-7200 words of body text.
DO NOT write short summaries — write FULL academic content with depth, analysis, and citations.

CRITICAL RULE-5: Every claim in the paper must be traceable to a source. Use citation keys [1], [2], etc.

STRICT EVIDENCE GROUNDING RULES:
- NEVER fabricate citations, references, or author names. Only use citations provided in the Available Citations list.
- NEVER invent benchmark results, datasets, accuracy percentages, or performance statistics.
- NEVER claim experiments were conducted if they were not. This is a literature review, not an experimental paper.
- NEVER use placeholder terms (e.g. "Indian Food", "ANFIS") unless they are the actual topic.
- If insufficient evidence exists for a claim, explicitly write: "This aspect requires further empirical investigation."
- Do NOT generate fake tables with fabricated numbers. Only include tables if real data is available from sources.
- Every paragraph making a factual claim MUST include at least one citation key [N].

Output valid JSON:
{
    "title": "Paper title",
    "abstract": "200-250 word abstract",
    "sections": [
        {
            "heading": "I. INTRODUCTION",
            "content": "Full section content (800+ words) with inline citations [1]...",
            "subsections": [
                {"heading": "A. Subsection", "content": "Detailed subsection content (300+ words)..."}
            ]
        }
    ],
    "conclusion": "Detailed concluding section (400+ words)"
}

Writing Rules:
- Academic, formal, human-like scholarly tone.
- Avoid repetitive AI/LLM transition patterns (such as 'Furthermore', 'Moreover', 'In conclusion', 'It is crucial to note', 'Indeed', 'Testament to', 'As shown in').
- Avoid generic conclusions or template paragraphs. Use domain-specific terminology, critical analysis, comparative discussion, and novel insights.
- Do NOT copy source sentences. Paraphrase all claims aggressively to maintain plagiarism < 4% and AI detection < 5%.
- Every factual claim must have a citation
- Use IEEE section numbering (I, II, III...) with ALL CAPS headings
- MANDATORY sections: Introduction, Literature Review, Methodology, Findings, Discussion, Limitations, Conclusion
- Abstract MUST be 200-250 words
- Each main section MUST be 600-1200 words minimum
- Include equations where relevant: $$equation$$ format
- Do NOT include any claim that lacks a citation
- Use precise, technical language
- Maintain logical flow between sections
- The paper must be COMPLETE and PUBLICATION-READY"""


class WriterAgent(BaseAgent):
    name = "writer"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()

        research_question = input_data.get("research_question", "")
        verified_claims = input_data.get("verified_claims", [])
        critiques = input_data.get("critiques", [])
        novelty = input_data.get("novelty", {})
        citations = input_data.get("citations", [])
        expected_sections = input_data.get("expected_sections", [])
        target_pages = input_data.get("pages", 12)
        page_budget = input_data.get("page_budget", {})
        target_word_count = input_data.get("target_word_count", 6000)
        topic = input_data.get("topic") or input_data.get("prompt") or research_question
        keywords = input_data.get("keywords") or []

        # Build context for writing
        claims_with_citations = []
        for i, claim in enumerate(verified_claims[:30]):
            citation_key = f"[{i+1}]"
            claims_with_citations.append(f"{claim} {citation_key}")

        novelty_text = ""
        if novelty:
            novel_contribs = "\n".join(f"- {c}" for c in novelty.get("novel_contributions", []))
            gaps = "\n".join(f"- {g}" for g in novelty.get("research_gaps", []))
            novelty_text = f"\nNovel Contributions:\n{novel_contribs}\n\nResearch Gaps:\n{gaps}"

        citations_text = "\n".join(
            f"{c.get('key', f'[{i+1}]')}: {c.get('ieee_format', c.get('title', ''))}"
            for i, c in enumerate(citations[:30])
        )

        # Build word budget instructions
        budget_instructions = self._build_budget_instructions(
            page_budget, target_word_count, target_pages
        )

        user_prompt = f"""Research Question: {research_question}
Topic: {topic}
Keywords: {', '.join(keywords) if keywords else ''}

Verified Claims (with citation keys):
{chr(10).join(claims_with_citations)}

{novelty_text}

Available Citations:
{citations_text}

Expected Sections: {', '.join(expected_sections) if expected_sections else 'Standard academic structure'}

{budget_instructions}

Write a FULL-LENGTH academic paper. Every claim MUST have a citation reference.
Each section must meet its minimum word count. The total body must be at least {target_word_count} words."""

        result = await llm.complete_json(
            role=AgentRole.WRITER,
            system_prompt=WRITER_SYSTEM,
            user_prompt=user_prompt,
        )

        # Enforce hard topic lock on every generated paragraph
        from services.relevance_checker import ensure_paragraph_relevance

        async def clean_text(text: str) -> str:
            if not text:
                return ""
            paragraphs = text.split("\n\n")
            cleaned_paragraphs = []
            for p in paragraphs:
                if p.strip():
                    cleaned_p = await ensure_paragraph_relevance(p, topic, keywords)
                    cleaned_paragraphs.append(cleaned_p)
                else:
                    cleaned_paragraphs.append(p)
            return "\n\n".join(cleaned_paragraphs)

        abstract = await clean_text(result.get("abstract", ""))
        conclusion = await clean_text(result.get("conclusion", ""))
        
        sections = result.get("sections", [])
        for sec in sections:
            sec["content"] = await clean_text(sec.get("content", ""))
            for sub in sec.get("subsections", []):
                sub["content"] = await clean_text(sub.get("content", ""))

        output = WriterOutput(
            title=result.get("title", "Untitled Research Paper"),
            abstract=abstract,
            sections=sections,
            conclusion=conclusion,
        )
        return output.model_dump()

    def _build_budget_instructions(
        self, page_budget: dict, target_word_count: int, target_pages: int
    ) -> str:
        """Build word count budget instructions for the LLM prompt."""
        if not page_budget:
            return f"""
=== WORD COUNT REQUIREMENTS ===
Target: {target_pages} pages = {target_word_count} words minimum
Each section must be 600-1200 words. Do not write short sections."""

        section_budgets = page_budget.get("section_budgets", {})
        if not section_budgets:
            return f"""
=== WORD COUNT REQUIREMENTS ===
Target: {target_pages} pages = {target_word_count} words minimum
Each section must be 600-1200 words. Do not write short sections."""

        lines = [
            f"\n=== MANDATORY WORD COUNT BUDGET ({target_pages} pages) ===",
            f"Total body word target: {target_word_count} words",
            "",
            "Section word minimums (MUST be met):",
        ]
        for section_name, budget in section_budgets.items():
            min_words = budget.get("min_words", 500)
            lines.append(f"  - {section_name}: {min_words} words minimum")

        lines.append("")
        lines.append("DO NOT write sections shorter than their budget.")
        lines.append("Include subsections, equations, tables, and analysis to reach targets.")
        return "\n".join(lines)

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return (
            bool(data.get("title"))
            and bool(data.get("abstract"))
            and len(data.get("sections", [])) >= 3
        )
