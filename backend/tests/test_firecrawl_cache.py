import hashlib
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas.agents import BrowsedPage
from services.firecrawl_service import FirecrawlService


@pytest.mark.asyncio
async def test_firecrawl_caching():
    service = FirecrawlService()
    service._api_key = "test-key"
    
    # Force _redis_client to use the in-memory dictionary fallback cache
    service._redis_client = "in_memory"
    service._in_memory_cache.clear()
    
    url = "https://example.com/cached-page"
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    
    mock_sdk_page = BrowsedPage(
        url=url,
        title="Original Title from SDK",
        content="This is the original scraped content.",
        content_type="markdown",
        word_count=50,
        extraction_quality=0.9,
    )
    
    mock_sdk = AsyncMock(return_value=mock_sdk_page)
    
    with patch.object(service, "_scrape_via_sdk", new=mock_sdk):
        # 1. First call: Cache miss, hits SDK
        res1 = await service.scrape(url)
        assert res1.title == "Original Title from SDK"
        assert mock_sdk.call_count == 1
        
        # Verify it was cached under the sha256 hash
        assert expected_hash in service._in_memory_cache
        
        # 2. Second call: Cache hit, returns immediately without calling SDK again
        res2 = await service.scrape(url)
        assert res2.title == "Original Title from SDK"
        assert mock_sdk.call_count == 1  # Verify call count didn't increase
