"""
Agent 3: Browser Agent
Browses URLs and extracts web page content.
"""

from agents.base import BaseAgent
from services.browser_service import get_browser_service
from services.document_store import get_document_store
from schemas.agents import BrowserOutput


class BrowserAgent(BaseAgent):
    name = "browser"

    async def execute(self, input_data: dict, context: dict) -> dict:
        browser = get_browser_service()
        doc_store = get_document_store()

        search_results = input_data.get("results", [])
        max_pages = input_data.get("max_pages", 15)

        # Get URLs to browse
        urls = [r["url"] for r in search_results[:max_pages] if r.get("url")]

        # Browse pages
        pages = await browser.browse_multiple(urls)

        # Filter out failed pages and deduplicate
        valid_pages = [p for p in pages if p.word_count > 50]
        valid_pages = doc_store.deduplicate_pages(valid_pages)

        failed = [p.url for p in pages if p.word_count <= 50]

        output = BrowserOutput(
            pages=valid_pages,
            failed_urls=failed,
        )

        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return len(data.get("pages", [])) > 0
