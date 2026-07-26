import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from config.settings import get_settings
from services.llm_manager import get_llm_manager


@pytest.fixture(autouse=True)
def clean_tracker(monkeypatch):
    from services.llm_manager import LLMManager
    from services.quota_tracker import reset_quota_tracker

    reset_quota_tracker()
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMMA_API_KEY", "")
    monkeypatch.setenv("MANUS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")

    from config.settings import get_settings

    get_settings.cache_clear()

    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    LLMManager._model_diagnostics = {}


@pytest.mark.asyncio
async def test_grok_api_call_fallback_to_mock(monkeypatch):
    # Clear all real keys to force mock fallback immediately
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMMA_API_KEY", "")
    monkeypatch.setenv("MANUS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    mock_post = AsyncMock()
    mock_client = MagicMock()
    mock_client.post = mock_post

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)

    res = await mgr.generate(
        prompt="hello grok", role=AgentRole.SEARCH, provider="grok", system_prompt="system inst"
    )

    # Assert it fell back to mock-fallback completion successfully
    assert res is not None
    assert "mock" in res.lower() or "search" in res.lower()

    # Verify no HTTP POST requests were sent to Grok since it is bypassed
    assert not mock_post.called
