import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from services.llm_manager import get_llm_manager


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from httpx import Request

            Request("POST", "http://test")
            # We raise a basic HTTP status error or Exception
            raise Exception(f"HTTP {self.status_code}")


@pytest.mark.asyncio
async def test_gemini_api_call(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    mgr = get_llm_manager()
    from config.settings import get_settings

    get_settings.cache_clear()
    mgr.settings = get_settings()

    # Setup mock response
    resp_data = {
        "candidates": [{"content": {"parts": [{"text": "Gemini response text"}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
    }

    mock_post = AsyncMock(return_value=MockResponse(200, resp_data))
    mock_client = MagicMock()
    mock_client.post = mock_post

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)

    res = await mgr.generate(
        prompt="hello gemini",
        role=AgentRole.PLANNER,
        provider="gemini",
        system_prompt="system inst",
    )

    assert res == "Gemini response text"
    assert mock_post.called

    # Verify request payload structure
    args, kwargs = mock_post.call_args
    url = args[0]
    assert "gemini-2.5-flash:generateContent" in url
    assert "key=test-gemini-key" in url

    req_body = kwargs["json"]
    assert req_body["contents"][0]["parts"][0]["text"] == "hello gemini"
    assert req_body["systemInstruction"]["parts"][0]["text"] == "system inst"
