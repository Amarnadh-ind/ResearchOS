"""
Web Search Service
Uses DuckDuckGo (zero-config) with Tavily upgrade path.
"""

import structlog
from duckduckgo_search import DDGS

from config.settings import get_settings
from schemas.agents import SearchResult

logger = structlog.get_logger()


class WebSearchService:
    """Web search with DuckDuckGo (default) and Tavily (optional)."""

    def __init__(self):
        self.settings = get_settings()
        self._use_tavily = bool(self.settings.tavily_api_key)

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Execute a web search query."""
        if self._use_tavily:
            return await self._search_tavily(query, max_results)
        return await self._search_ddg(query, max_results)

    async def _search_ddg(
        self, query: str, max_results: int
    ) -> list[SearchResult]:
        """Search using DuckDuckGo (no API key needed)."""
        try:
            results = []
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                    results.append(
                        SearchResult(
                            title=r.get("title", ""),
                            url=r.get("href", r.get("link", "")),
                            snippet=r.get("body", r.get("snippet", "")),
                            relevance_score=1.0 - (i * 0.05),
                        )
                    )
            logger.info("search_ddg", query=query, results=len(results))
            return results
        except Exception as e:
            logger.error("search_ddg_error", query=query, error=str(e))
            return []

    async def _search_tavily(
        self, query: str, max_results: int
    ) -> list[SearchResult]:
        """Search using Tavily API."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.settings.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_raw_content": False,
                        "search_depth": "advanced",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for i, r in enumerate(data.get("results", [])):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        relevance_score=r.get("score", 1.0 - (i * 0.05)),
                    )
                )
            logger.info("search_tavily", query=query, results=len(results))
            return results
        except Exception as e:
            logger.error("search_tavily_error", error=str(e))
            # Fallback to DuckDuckGo
            return await self._search_ddg(query, max_results)

    async def multi_search(
        self, queries: list[str], max_results_per_query: int = 8
    ) -> list[SearchResult]:
        """Execute multiple search queries in parallel and deduplicate results."""
        import asyncio

        tasks = [self.search(query, max_results_per_query) for query in queries]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for results in batch_results:
            if isinstance(results, Exception):
                logger.error("multi_search_query_error", error=str(results))
                continue
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)

        # Sort by relevance
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_results


_search_service: WebSearchService | None = None


def get_search_service() -> WebSearchService:
    global _search_service
    if _search_service is None:
        _search_service = WebSearchService()
    return _search_service
