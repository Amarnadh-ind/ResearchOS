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
def clean_discovery(monkeypatch):
    """Reset the discovered status and lists before each test."""
    from services.quota_tracker import reset_quota_tracker

    reset_quota_tracker()

    # Clear all keys from env/settings to prevent leaks
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
    LLMManager._discovered_status = {"manus": "untested", "gemma": "untested", "gemini": "untested"}


def setup_mock_client(monkeypatch, mock_post_fn):
    """Utility to setup a mock httpx.AsyncClient with mock get and post functions."""

    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            resp_data = {
                "models": [
                    {
                        "name": "models/gemma-4-31b-it",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemma-4-26b-a4b-it",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-flash-lite",
                        "supportedGenerationMethods": ["generateContent"],
                    },
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
async def test_manus_only_mode(monkeypatch, capsys):
    """Test that when LLM_PROVIDER=manus, we only try Manus and then fall back to mock-fallback."""
    monkeypatch.setenv("LLM_PROVIDER", "manus")
    monkeypatch.setenv("MANUS_API_KEY", "test-manus-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Manus rate limit")

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()

    # Run generate
    res = await mgr.generate(
        prompt="Test Manus only mode", role=AgentRole.PLANNER, provider="manus"
    )

    assert res is not None
    # Verify only Manus was called (and no Gemma or Gemini URLs)
    assert len(called_urls) == 1
    assert "manus" in called_urls[0]

    captured = capsys.readouterr()
    stdout = captured.out

    assert "provider_attempt=manus" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=mock-fallback" in stdout
    assert "provider_success=true" in stdout  # mock fallback succeeds


@pytest.mark.asyncio
async def test_manus_to_gemini_failover(monkeypatch, capsys):
    """Test that when Manus fails, it falls back directly to Gemini if Gemma keys are missing."""
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("MANUS_API_KEY", "test-manus-key")
    monkeypatch.setenv("GEMMA_API_KEY", "")  # Gemma disabled
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        if "manus" in url:
            return httpx.Response(status_code=429, request=req, text="Manus rate limit")
        else:
            # Gemini response
            resp_data = {
                "candidates": [{"content": {"parts": [{"text": "Gemini fallback response"}]}}],
                "usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 25},
            }
            return httpx.Response(status_code=200, request=req, json=resp_data)

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()
    LLMManager._discovered_gemma_models = []
    LLMManager._build_routing_pool()

    res = await mgr.generate(
        prompt="Test Manus to Gemini failover", role=AgentRole.PLANNER, provider="auto"
    )

    assert res == "Gemini fallback response"
    assert len(called_urls) == 2
    assert "manus" in called_urls[0]
    assert "gemini-2.5-flash" in called_urls[1]

    captured = capsys.readouterr()
    stdout = captured.out

    assert "provider_attempt=manus" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemini-2.5-flash" in stdout
    assert "provider_attempt=gemini-2.5-flash" in stdout
    assert "provider_success=true" in stdout


@pytest.mark.asyncio
async def test_manus_to_gemma_failover(monkeypatch, capsys):
    """Test that when Manus fails, it falls back to Gemma."""
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("MANUS_API_KEY", "test-manus-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "")  # Gemini disabled

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        if "manus" in url:
            return httpx.Response(status_code=402, request=req, text="Manus payment required")
        else:
            # Gemma response
            resp_data = {
                "candidates": [{"content": {"parts": [{"text": "Gemma fallback response"}]}}],
                "usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 25},
            }
            return httpx.Response(status_code=200, request=req, json=resp_data)

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()
    LLMManager._discovered_gemini_models = []
    LLMManager._build_routing_pool()

    res = await mgr.generate(
        prompt="Test Manus to Gemma failover", role=AgentRole.PLANNER, provider="auto"
    )

    assert res == "Gemma fallback response"
    assert len(called_urls) == 2
    assert "manus" in called_urls[0]
    assert "gemma-4-31b-it" in called_urls[1]

    captured = capsys.readouterr()
    stdout = captured.out

    assert "provider_attempt=manus" in stdout
    assert "provider_failed=402" in stdout
    assert "fallback_to=gemma-4-31b-it" in stdout
    assert "provider_attempt=gemma-4-31b-it" in stdout
    assert "provider_success=true" in stdout


@pytest.mark.asyncio
async def test_full_manus_routing_chain(monkeypatch, capsys):
    """Test that all models fail and it goes down to mock-fallback in priority order."""
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("MANUS_API_KEY", "test-manus-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        # Timeout/Rate limit/Auth error simulation: return 429
        return httpx.Response(status_code=429, request=req, text="Rate limit")

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()

    # Run generate
    res = await mgr.generate(prompt="Test full chain", role=AgentRole.PLANNER, provider="auto")

    assert res is not None
    # Verify we hit all 5 configured models before falling back to mock
    assert len(called_urls) == 5
    assert "manus" in called_urls[0]
    assert "gemini-2.5-flash" in called_urls[1]
    assert "gemini-2.5-flash-lite" in called_urls[2]
    assert "gemma-4-31b-it" in called_urls[3]
    assert "gemma-4-26b-a4b-it" in called_urls[4]

    captured = capsys.readouterr()
    stdout = captured.out

    # Assert logs contain the correct routing priority
    assert "provider_attempt=manus" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemini-2.5-flash" in stdout

    assert "provider_attempt=gemini-2.5-flash" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemini-2.5-flash-lite" in stdout

    assert "provider_attempt=gemini-2.5-flash-lite" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemma-4-31b-it" in stdout

    assert "provider_attempt=gemma-4-31b-it" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=gemma-4-26b-a4b-it" in stdout

    assert "provider_attempt=gemma-4-26b-a4b-it" in stdout
    assert "provider_failed=429" in stdout
    assert "fallback_to=mock-fallback" in stdout

    assert "provider_success=true" in stdout
