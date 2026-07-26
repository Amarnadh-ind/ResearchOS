import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from config.settings import get_settings
from services.llm_manager import LLMManager, get_llm_manager


@pytest.fixture(autouse=True)
def clean_tracker():
    from services.quota_tracker import reset_quota_tracker

    reset_quota_tracker()
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    LLMManager._model_diagnostics = {}


@pytest.mark.asyncio
async def test_gemma_provider_success(monkeypatch):
    # Set Gemma key
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    # Mock HTTP client to succeed on Gemma
    called_urls = []

    async def mock_post(url, json, *args, **kwargs):
        called_urls.append(url)
        resp_data = {
            "candidates": [{"content": {"parts": [{"text": "Gemma model response text"}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 200},
        }
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=200, request=req, json=resp_data)

    mock_client = MagicMock()
    mock_client.post = mock_post

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)

    # Run generate with preferred provider "gemma"
    res = await mgr.generate(prompt="hello gemma", role=AgentRole.WRITER, provider="gemma")

    assert res == "Gemma model response text"
    assert len(called_urls) == 1
    assert "gemma-4-31b-it" in called_urls[0]
    assert "key=test-gemma-key" in called_urls[0]

    # Verify diagnostics updated
    diag = LLMManager._model_diagnostics.get("gemma-4-31b-it", {})
    assert diag.get("connected") is True
    assert diag.get("last_status") == 200
    assert diag.get("latency") >= 0
