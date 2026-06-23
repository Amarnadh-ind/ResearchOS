"""
Agent 7: Novelty Agent
Assesses research novelty and identifies gaps.
"""

from agents.base import BaseAgent
from config.models import AgentRole
from schemas.agents import NoveltyAssessment
from services.llm import get_llm_client

NOVELTY_SYSTEM = """You are a research novelty assessment specialist. Analyze the collected research claims and identify:

1. What is genuinely novel or underexplored
2. Where the research overlaps with existing work
3. What gaps exist in the current literature
4. What angles could provide unique contributions

Output valid JSON:
{
    "novelty_score": 0.0-1.0,
    "novel_contributions": ["list of potentially novel contributions this research could make"],
    "existing_work_overlap": ["areas where significant prior work already exists"],
    "research_gaps": ["identified gaps in the current literature"],
    "suggested_angles": ["suggested unique angles for the paper"]
}

Be specific and actionable. Avoid generic statements."""


class NoveltyAgent(BaseAgent):
    name = "novelty"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()

        research_question = input_data.get("research_question", "")
        verified_claims = input_data.get("verified_claims", [])
        critiques = input_data.get("critiques", [])

        claims_summary = "\n".join(f"- {c}" for c in verified_claims[:20])
        critique_summary = "\n".join(
            f"- {c.get('claim', '')}: {c.get('evidence_quality', '')}"
            for c in critiques[:15]
        )

        user_prompt = f"""Research Question: {research_question}

Verified Claims:
{claims_summary}

Evidence Quality Assessment:
{critique_summary}

Analyze the novelty of this research area and identify gaps and opportunities."""

        result = await llm.complete_json(
            role=AgentRole.NOVELTY,
            system_prompt=NOVELTY_SYSTEM,
            user_prompt=user_prompt,
        )

        assessment = NoveltyAssessment(**result)
        return assessment.model_dump()
