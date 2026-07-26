import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.firecrawl_extract import FirecrawlExtractAgent
from schemas.agents import BrowsedPage


@pytest.mark.asyncio
async def test_firecrawl_extract_agent():
    # Construct a mock BrowsedPage output representing a successful Firecrawl scrape
    mock_page = BrowsedPage(
        url="https://example.com/test",
        title="Mock Test Title",
        content="This is a mock page content with more than fifty words to satisfy the length filters. "
        * 5,
        content_type="markdown",
        word_count=60,
        extraction_quality=0.9,
        publication_date="2026-06-16",
        author="Test Author",
        site_name="Test Site",
        description="Test description",
    )

    agent = FirecrawlExtractAgent()

    with patch(
        "services.firecrawl_service.FirecrawlService.batch_scrape", new_callable=AsyncMock
    ) as mock_batch:
        mock_batch.return_value = [mock_page]

        input_data = {
            "results": [
                {"url": "https://example.com/test", "relevance_score": 0.9, "source_quality": 0.8}
            ],
            "max_pages": 5,
        }

        result = await agent.execute(input_data, {})

        # Verify the agent returned pages array with correct data
        assert "pages" in result
        assert len(result["pages"]) == 1
        page = result["pages"][0]

        # Verify both old and new schema properties are accessible
        assert page["url"] == "https://example.com/test"
        assert page["title"] == "Mock Test Title"
        assert "more than fifty words" in page["content"]
        assert page["author"] == "Test Author"
        assert page["publication_date"] == "2026-06-16"

        # Verify firecrawl diagnostics stats exist in returned dict
        assert "firecrawl_requests" in result
        assert "firecrawl_success" in result
        assert "firecrawl_failed" in result
        assert "firecrawl_latency_ms" in result
