"""
Agent 3: Firecrawl Extract Agent
Extracts web page content via Firecrawl with HTTP BeautifulSoup fallback.
"""

import structlog

from agents.base import BaseAgent
from schemas.agents import BrowserOutput
from services.document_store import get_document_store
from services.firecrawl_service import get_firecrawl_service

logger = structlog.get_logger()


class FirecrawlExtractAgent(BaseAgent):
    name = "firecrawl_extract"

    async def execute(self, input_data: dict, context: dict) -> dict:
        firecrawl = get_firecrawl_service()
        doc_store = get_document_store()

        search_results = input_data.get("results", [])
        max_pages = input_data.get("max_pages", 15)

        # Deduplicate URLs from search results immediately
        seen = set()
        unique_results = []
        for r in search_results:
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique_results.append(r)
        search_results = unique_results

        # Get URLs to browse, ranked by combined relevance+quality
        scored = []
        for r in search_results[:max_pages]:
            score = r.get("relevance_score", 0.5) * 0.5 + r.get("source_quality", 0.5) * 0.5
            scored.append((score, r["url"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        urls = [url for _, url in scored]

        if not urls:
            return BrowserOutput(pages=[], failed_urls=[]).model_dump()

        # Browse via Firecrawl (primary) or BeautifulSoup fallback
        pages = await firecrawl.batch_scrape(urls)

        # Filter out failed pages
        valid_pages = [p for p in pages if p.word_count > 50 and p.content_type != "error"]

        # Deduplicate by content hash
        valid_pages = doc_store.deduplicate_pages(valid_pages)

        # Sort by extraction quality descending
        valid_pages.sort(key=lambda p: p.extraction_quality, reverse=True)

        failed = [p.url for p in pages if p.word_count <= 50 or p.content_type == "error"]

        logger.info(
            "firecrawl_extract_completed",
            requested=len(urls),
            succeeded=len(valid_pages),
            failed=len(failed),
        )

        output = BrowserOutput(
            pages=valid_pages,
            failed_urls=failed,
        )

        res = output.model_dump()
        # Add firecrawl diagnostics to the agent output data
        res["firecrawl_requests"] = firecrawl.firecrawl_requests
        res["firecrawl_success"] = firecrawl.firecrawl_success
        res["firecrawl_failed"] = firecrawl.firecrawl_failed
        res["firecrawl_latency_ms"] = firecrawl.firecrawl_latency_ms

        return res

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return len(data.get("pages", [])) > 0
