import sys
import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm_manager import get_llm_manager, LLMManager
from config.models import AgentRole
from config.settings import get_settings


@pytest.fixture(autouse=True)
def clean_discovery():
    """Reset the discovered status and lists before each test."""
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_status = {
        "manus": "untested",
        "gemma": "untested",
        "gemini": "untested"
    }


def setup_mock_client(monkeypatch, mock_post_fn):
    """Utility to setup a mock httpx.AsyncClient with mock get and post functions."""
    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            resp_data = {
                "models": [
                    {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemma-4-26b-a4b-it", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemini-2.5-flash-lite", "supportedGenerationMethods": ["generateContent"]}
                ]
            }
            return httpx.Response(status_code=200, request=req, json=resp_data)
        return httpx.Response(status_code=404, request=req)

    mock_client = MagicMock()
    mock_client.post = mock_post_fn
    mock_client.get = mock_get
    
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)
    return mock_async_client


@pytest.mark.asyncio
async def test_full_failover_chain_gemma_to_gemini_to_mock(monkeypatch, capsys):
    # Set both API keys
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("MANUS_API_KEY", "")  # manus disabled for this test
    
    # Reload settings
    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()
    
    # Mock HTTP client to fail all real LLM models with 429
    called_urls = []
    
    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")
        
    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()
    
    # Run generate
    res = await mgr.generate(
        prompt="Test failover",
        role=AgentRole.PLANNER,
        provider="auto"
    )
    
    # Since all real LLMs failed, it must fall back to mock and complete successfully
    assert res is not None
    assert "mock" in res.lower() or "planner" in res.lower() or len(res) > 0
    
    # Verify the chain: gemma-4-31b-it -> gemma-4-26b-a4b-it -> gemini-2.5-flash -> gemini-2.5-flash-lite
    assert any("gemma-4-31b-it" in url for url in called_urls)
    assert any("gemma-4-26b-a4b-it" in url for url in called_urls)
    assert any("gemini-2.5-flash" in url for url in called_urls)
    assert any("gemini-2.5-flash-lite" in url for url in called_urls)
    
    # Check stdout logs for failover messages
    captured = capsys.readouterr()
    stdout = captured.out
    
    assert "provider_attempt=gemma-4-31b-it" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemma-4-26b-a4b-it" in stdout
    
    assert "provider_attempt=gemma-4-26b-a4b-it" in stdout
    assert "fallback_to=gemini-2.5-flash" in stdout
    
    assert "provider_attempt=gemini-2.5-flash" in stdout
    assert "fallback_to=gemini-2.5-flash-lite" in stdout
    
    assert "provider_attempt=gemini-2.5-flash-lite" in stdout
    assert "fallback_to=mock-fallback" in stdout
    assert "provider_success=true" in stdout


@pytest.mark.asyncio
async def test_missing_keys_routing(monkeypatch, capsys):
    # Set only GEMINI key, GEMMA key missing
    monkeypatch.setenv("GEMMA_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("MANUS_API_KEY", "")  # manus disabled for this test
    
    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()
    
    # Mock HTTP client to succeed on the first call (which should be Gemini Flash, since Gemma is skipped)
    called_urls = []
    
    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        resp_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini direct response"}]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20
            }
        }
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=200, request=req, json=resp_data)
        
    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()
    
    res = await mgr.generate(
        prompt="Test missing key",
        role=AgentRole.PLANNER,
        provider="auto"
    )
    
    assert res == "Gemini direct response"
    # Ensure no Gemma models were attempted
    assert len(called_urls) == 1
    assert "gemini-2.5-flash" in called_urls[0]
    assert not any("gemma" in url for url in called_urls)
    
    captured = capsys.readouterr()
    stdout = captured.out
    assert "provider_attempt=gemini-2.5-flash" in stdout
    assert "provider_success=true" in stdout
    assert "provider_attempt=gemma" not in stdout
