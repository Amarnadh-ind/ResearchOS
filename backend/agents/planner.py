"""
Agent 1: Planner Agent
Decomposes research prompts into structured research plans.
"""

import json
from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import ResearchPlan


PLANNER_SYSTEM = """You are a research planning specialist. Given a research prompt, create a comprehensive research plan.

You must output valid JSON with this exact structure:
{
    "research_question": "The refined, specific research question",
    "sub_questions": ["list of 3-6 sub-questions to investigate"],
    "search_queries": ["list of 5-10 specific search queries to find relevant sources"],
    "methodology": "Brief description of the research methodology",
    "expected_sections": ["list of expected paper sections"],
    "key_concepts": ["list of key concepts to investigate"],
    "primary_topic": "The primary specific topic (e.g. Electric Vehicles)",
    "secondary_topics": ["list of 2-4 secondary topics"],
    "keywords": ["list of 5-10 relevant keywords for topic locking"],
    "technical_domain": "The broad technical domain"
}

Rules:
- Make search queries specific and academic-oriented
- Include both broad and narrow queries
- Sub-questions should cover different facets of the topic
- Expected sections should follow academic paper structure
- Key concepts should be precise technical terms"""


class PlannerAgent(BaseAgent):
    name = "planner"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()
        prompt = input_data.get("prompt", "")
        depth = input_data.get("depth", "standard")

        user_prompt = f"""Research Prompt: {prompt}
Research Depth: {depth}

Create a comprehensive research plan. Return valid JSON only."""

        result = await llm.complete_json(
            role=AgentRole.PLANNER,
            system_prompt=PLANNER_SYSTEM,
            user_prompt=user_prompt,
        )

        plan = ResearchPlan(**result)
        return plan.model_dump()

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return (
            bool(data.get("research_question"))
            and len(data.get("search_queries", [])) >= 3
            and len(data.get("sub_questions", [])) >= 2
        )
