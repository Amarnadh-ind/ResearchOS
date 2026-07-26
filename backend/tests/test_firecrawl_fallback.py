import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas.agents import BrowsedPage
from services.firecrawl_service import FirecrawlService


@pytest.mark.asyncio
async def test_firecrawl_fallback_to_bs4():
    service = FirecrawlService()
    service._api_key = "test-key"  # Force available = True

    # Mock successful BeautifulSoup fallback response
    mock_fallback_page = BrowsedPage(
        url="https://example.com/fallback",
        title="BeautifulSoup Fallback Title",
        content="Clean extracted markdown content from BS4 scraper.",
        content_type="text",
        word_count=7,
        extraction_quality=0.5,
    )

    # Mock SDK call to fail, prompting fallback
    async def mock_sdk(url, timeout):
        raise RuntimeError("Firecrawl SDK error simulation")

    async def mock_httpx(url, timeout):
        return mock_fallback_page

    with (
        patch.object(service, "_scrape_via_sdk", side_effect=mock_sdk),
        patch.object(service, "_scrape_via_httpx", side_effect=mock_httpx),
    ):
        # Reset diagnostics count for testing
        service.firecrawl_requests = 0
        service.firecrawl_success = 0
        service.firecrawl_failed = 0

        result = await service.scrape("https://example.com/fallback")

        # Assert result is from the fallback BeautifulSoup scraper
        assert result.title == "BeautifulSoup Fallback Title"
        assert result.content == "Clean extracted markdown content from BS4 scraper."
        assert result.content_type == "text"

        # Verify diagnostics
        assert service.firecrawl_requests == 1
        assert service.firecrawl_failed == 1
        assert service.firecrawl_success == 0
        assert service.status == "offline"
        assert "Firecrawl SDK error simulation" in service.last_error
