import sys
import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm import get_llm_client
from config.models import AgentRole
from config.settings import get_settings

@pytest.mark.asyncio
async def test_mock_mode_disabled_when_provider_configured(monkeypatch):
    # Configure Gemini API key
    monkeypatch.setenv("GEMINI_API_KEY", "valid-gemini-key")
    monkeypatch.setenv("GEMMA_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    from services.llm_manager import get_llm_manager
    get_llm_manager().settings = get_settings()
    
    client = get_llm_client()
    
    # Mock Gemini to succeed
    resp_data = {
        "candidates": [{"content": {"parts": [{"text": "Real LLM Output"}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
    }
    
    async def mock_post(url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            req = httpx.Request("POST", url)
            return httpx.Response(status_code=200, request=req, json=resp_data)
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=404, request=req)
        
    mock_client = MagicMock()
    mock_client.post = mock_post
    
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)
    
    res = await client.complete(
        role=AgentRole.PLANNER,
        system_prompt="system",
        user_prompt="user"
    )
    
    # Assertions
    assert res == "Real LLM Output"

@pytest.mark.asyncio
async def test_mock_mode_falls_back_to_mock_when_all_fail(monkeypatch):
    # Configure Gemini key
    monkeypatch.setenv("GEMINI_API_KEY", "failed-gemini-key")
    monkeypatch.setenv("GEMMA_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    from services.llm_manager import get_llm_manager
    get_llm_manager().settings = get_settings()
    
    client = get_llm_client()
    
    # Mock Gemini to fail (500)
    async def mock_post(url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=500, request=req, text="Internal Error")
        
    mock_client = MagicMock()
    mock_client.post = mock_post
    
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)
    
    # Under new requirements, it should fall back to mock-fallback and return successfully
    res = await client.complete(
        role=AgentRole.PLANNER,
        system_prompt="system",
        user_prompt="user"
    )
    assert res is not None
    assert len(res) > 0
