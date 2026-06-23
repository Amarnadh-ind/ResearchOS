"""Agent 11: Humanizer Agent
Section-level humanization — all sections processed in parallel."""

import copy

from agents.base import BaseAgent
from config.models import AgentRole
from services.llm import get_llm_client

HUMANIZER_SYSTEM = """You are an academic writing optimizer and paraphrasing specialist.
Your task is to rewrite the given academic paper section to:
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
            humanized_text = await self._humanize_section_text(text)
            return {"text": humanized_text}

        paper_copy = copy.deepcopy(paper)
        sections_to_humanize = []

        abstract = paper_copy.get("abstract", "")
        if abstract:
            sections_to_humanize.append(("abstract", abstract))
            paper_copy["abstract"] = ""

        conclusion = paper_copy.get("conclusion", "")
        if conclusion:
            sections_to_humanize.append(("conclusion", conclusion))
            paper_copy["conclusion"] = ""

        sections = paper_copy.get("sections", [])
        for i, sec in enumerate(sections):
            content = sec.get("content", "")
            if content:
                sections_to_humanize.append((f"section_{i}", content))
                sec["content"] = ""

        if sections_to_humanize:
            import asyncio
            tasks = [self._humanize_section_text(text) for _, text in sections_to_humanize]
            results = await asyncio.gather(*tasks)

            for (key, _), humanized in zip(sections_to_humanize, results):
                if key == "abstract":
                    paper_copy["abstract"] = humanized
                elif key == "conclusion":
                    paper_copy["conclusion"] = humanized
                elif key.startswith("section_"):
                    idx = int(key.split("_")[1])
                    paper_copy["sections"][idx]["content"] = humanized

        return paper_copy

    async def humanize_paper(self, paper: dict) -> dict:
        """Convenience method to humanize a full structured paper."""
        result = await self.run({"paper": paper}, {})
        if result.get("status") == "success":
            return result["data"]
        return paper

    async def _humanize_section_text(self, text: str) -> str:
        """Humanize an entire section in a single LLM call."""
        if not text.strip():
            return text

        llm = get_llm_client()
        user_prompt = (
            "Rewrite and humanize the following academic section to sound natural "
            "and original while preserving all technical meaning, citations, and equations:\n\n"
            f"{text}"
        )
        try:
            res = await llm.complete(
                role=AgentRole.HUMANIZER,
                system_prompt=HUMANIZER_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            res_clean = res.strip()
            if res_clean and len(res_clean) > len(text) * 0.4:
                return res_clean
        except Exception:
            pass
        return text
