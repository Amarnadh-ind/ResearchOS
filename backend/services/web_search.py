"""
Web Search Service
Uses DuckDuckGo (zero-config) with Tavily upgrade path.
Deduplicates URLs and computes source quality scores.
"""

from urllib.parse import urlparse

import structlog
from duckduckgo_search import DDGS

from config.settings import get_settings
from schemas.agents import SearchResult

logger = structlog.get_logger()

# Domains known for high-quality academic/technical content
HIGH_QUALITY_DOMAINS = {
    "arxiv.org", "ieee.org", "acm.org", "springer.com", "sciencedirect.com",
    "nature.com", "science.org", "plos.org", "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov", "cambridge.org", "oxfordjournals.org", "tandfonline.com",
    "wiley.com", "sagepub.com", "jstor.org", "researchgate.net", "semanticscholar.org",
    "scholar.google.com", "dblp.org", "ieeexplore.ieee.org", "dl.acm.org",
    "mit.edu", "stanford.edu", "harvard.edu", "ox.ac.uk", "cam.ac.uk",
    "github.com", "paperswithcode.com", "openreview.net", "neurips.cc",
    "iclr.cc", "cvf.io", "aaai.org", "ijcai.org",
}

MEDIUM_QUALITY_DOMAINS = {
    "medium.com", "towardsdatascience.com", "analyticsvidhya.com",
    "kaggle.com", "stackoverflow.com", "stackexchange.com",
    "wikipedia.org", "wikidata.org", "news.ycombinator.com",
    "techcrunch.com", "theverge.com", "venturebeat.com",
    "arxiv-vanity.com", "huggingface.co", "giters.com",
    "oreilly.com", "manning.com", "packtpub.com",
}


def _compute_source_quality(url: str, title: str, snippet: str) -> float:
    """Compute source quality score (0-1) based on domain and content signals."""
    score = 0.3

    try:
        domain = urlparse(url).netloc.lower()
        domain = domain.removeprefix("www.")
    except Exception:
        domain = ""

    if any(hq in domain for hq in HIGH_QUALITY_DOMAINS):
        score += 0.4
    elif any(mq in domain for mq in MEDIUM_QUALITY_DOMAINS):
        score += 0.2
    elif any(edu in domain for edu in [".edu", ".ac."]):
        score += 0.3
    elif any(gov in domain for gov in [".gov", ".org"]):
        score += 0.1

    title_len = len(title)
    if 20 <= title_len <= 200:
        score += 0.1

    snippet_len = len(snippet)
    if snippet_len > 80:
        score += 0.1
    if snippet_len > 200:
        score += 0.1

    return min(1.0, score)


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication: remove trailing slash, fragment, common tracking params."""
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        query = parsed.query
        clean = f"{parsed.scheme}://{parsed.netloc}{path}"
        if query:
            clean = f"{clean}?{query}"
        return clean
    except Exception:
        return url


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
            seen = set()
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(query, max_results=max_results * 2)):
                    url = r.get("href", r.get("link", ""))
                    normalized = _normalize_url(url)
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    title = r.get("title", "")
                    snippet = r.get("body", r.get("snippet", ""))
                    quality = _compute_source_quality(url, title, snippet)
                    results.append(
                        SearchResult(
                            title=title,
                            url=normalized,
                            snippet=snippet,
                            relevance_score=max(0.0, 1.0 - (i * 0.04)),
                            source_quality=quality,
                        )
                    )
                    if len(results) >= max_results:
                        break
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
                        "include_domains": [],
                        "exclude_domains": [],
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            seen = set()
            results = []
            for i, r in enumerate(data.get("results", [])):
                url = r.get("url", "")
                normalized = _normalize_url(url)
                if normalized in seen:
                    continue
                seen.add(normalized)
                title = r.get("title", "")
                snippet = r.get("content", "")
                quality = _compute_source_quality(normalized, title, snippet)
                results.append(
                    SearchResult(
                        title=title,
                        url=normalized,
                        snippet=snippet,
                        relevance_score=r.get("score", max(0.0, 1.0 - (i * 0.05))),
                        source_quality=quality,
                    )
                )
            logger.info("search_tavily", query=query, results=len(results))
            return results
        except Exception as e:
            logger.error("search_tavily_error", error=str(e))
            return await self._search_ddg(query, max_results)

    async def multi_search(
        self, queries: list[str], max_results_per_query: int = 8
    ) -> list[SearchResult]:
        """Execute multiple search queries in parallel, deduplicate, and rank by quality."""
        import asyncio

        tasks = [self.search(query, max_results_per_query) for query in queries]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        all_results: list[SearchResult] = []

        for results in batch_results:
            if isinstance(results, Exception):
                logger.error("multi_search_query_error", error=str(results))
                continue
            for r in results:
                normalized = _normalize_url(r.url)
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    r.url = normalized
                    all_results.append(r)

        # Combine relevance and quality into composite score
        for r in all_results:
            composite = r.relevance_score * 0.6 + r.source_quality * 0.4
            r.relevance_score = composite

        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_results


_search_service: WebSearchService | None = None


def get_search_service() -> WebSearchService:
    global _search_service
    if _search_service is None:
        _search_service = WebSearchService()
    return _search_service
