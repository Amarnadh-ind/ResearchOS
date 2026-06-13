"""
Agent 11: Humanizer Agent
Optimizes tone and structures to make text sound human-like and reduce plagiarism under 4%.
"""

import asyncio
import copy
from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole

HUMANIZER_SYSTEM = """You are an academic writing optimizer and paraphrasing specialist.
Your task is to rewrite the given academic paper section/paragraph to:
1. Ensure the tone is natural, professional, and completely free of AI-generated signatures (avoid clichés, robotic transition words, and repetitive sentence structures like 'Furthermore', 'Moreover', 'In conclusion', 'It is crucial to note', 'Indeed', 'Testament to', 'As shown in').
2. Aggressively paraphrase the text so that it has ZERO resemblance to any source material, ensuring a plagiarism score strictly under 4%.
3. Absolutely preserve all LaTeX mathematical equations (e.g. $$equation$$ or $equation$) and inline citations (e.g. [1], [2], etc.) exactly as they are. Do not alter, delete, or renumber them.
4. Keep the exact meaning, technical details, claims, and data points intact, but express them in a fresh, sophisticated academic style.
5. Do NOT summarize. The output must be of comparable length to the input.
6. Return only the rewritten text, with no preamble, introduction, or conversational filler."""


class HumanizerAgent(BaseAgent):
    name = "humanizer"

    async def execute(self, input_data: dict, context: dict) -> dict:
        paper = input_data.get("paper", {})
        if not paper:
            text = input_data.get("text", "")
            if not text:
                return {"text": ""}
            humanized_text = await self._humanize_text(text)
            return {"text": humanized_text}

        paper_copy = copy.deepcopy(paper)

        # 1. Humanize Abstract
        abstract = paper_copy.get("abstract", "")
        if abstract:
            paper_copy["abstract"] = await self._humanize_text(abstract)

        # 2. Humanize Conclusion
        conclusion = paper_copy.get("conclusion", "")
        if conclusion:
            paper_copy["conclusion"] = await self._humanize_text(conclusion)

        # 3. Humanize Sections
        sections = paper_copy.get("sections", [])
        if sections:
            tasks = []
            for sec in sections:
                tasks.append(self._humanize_section(sec))
            await asyncio.gather(*tasks)

        return paper_copy

    async def humanize_paper(self, paper: dict) -> dict:
        """Convenience method to humanize a full structured paper."""
        result = await self.run({"paper": paper}, {})
        if result.get("status") == "success":
            return result["data"]
        return paper

    async def _humanize_text(self, text: str) -> str:
        if not text.strip():
            return text

        paragraphs = text.split("\n\n")
        p_tasks = []
        p_indices = []

        for idx, p in enumerate(paragraphs):
            p_stripped = p.strip()
            if not p_stripped:
                continue

            # Skip markdown tables, HTML/SVG figure blocks, and math equations
            if p_stripped.startswith("|"):
                continue
            if p_stripped.startswith("<") and (p_stripped.endswith(">") or len(p_stripped) > 20):
                continue
            if p_stripped.startswith("$$") and p_stripped.endswith("$$"):
                continue

            p_indices.append(idx)
            p_tasks.append(self._humanize_paragraph(p))

        if p_tasks:
            rewritten_paragraphs = await asyncio.gather(*p_tasks)
            for idx, rewritten in zip(p_indices, rewritten_paragraphs):
                paragraphs[idx] = rewritten

        return "\n\n".join(paragraphs)

    async def _humanize_paragraph(self, paragraph: str) -> str:
        llm = get_llm_client()
        user_prompt = f"Rewrite and humanize this paragraph:\n\n{paragraph}"
        try:
            res = await llm.complete(
                role=AgentRole.HUMANIZER,
                system_prompt=HUMANIZER_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.3
            )
            res_clean = res.strip()
            if res_clean:
                # Safety fallback to original if output is too short (possible truncation/error)
                if len(res_clean) > len(paragraph) * 0.4:
                    return res_clean
        except Exception:
            pass
        return paragraph

    async def _humanize_section(self, section: dict):
        content = section.get("content", "")
        if content:
            section["content"] = await self._humanize_text(content)

        subsections = section.get("subsections", [])
        if subsections:
            tasks = []
            for sub in subsections:
                tasks.append(self._humanize_section(sub))
            await asyncio.gather(*tasks)
