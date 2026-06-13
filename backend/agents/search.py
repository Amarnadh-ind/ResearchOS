"""
Agent 2: Search Agent
Executes search queries and returns deduplicated results.
"""

from agents.base import BaseAgent
from services.web_search import get_search_service
from schemas.agents import SearchOutput


class SearchAgent(BaseAgent):
    name = "search"

    async def execute(self, input_data: dict, context: dict) -> dict:
        search_service = get_search_service()
        queries = input_data.get("search_queries", [])
        max_results = input_data.get("max_results", 8)

        all_results = await search_service.multi_search(
            queries=queries,
            max_results_per_query=max_results,
        )

        output = SearchOutput(
            queries_executed=queries,
            results=all_results,
            total_results=len(all_results),
        )

        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return data.get("total_results", 0) > 0
