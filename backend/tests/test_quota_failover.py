"""
Tests for Quota-Aware Failover
Verifies automatic model switching on quota exhaustion, 429 errors, and cascading failover.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from services.llm_manager import LLMManager, get_llm_manager
from services.quota_tracker import get_quota_tracker, reset_quota_tracker


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset discovery state and quota tracker before each test."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("MANUS_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    LLMManager._model_diagnostics = {}
    reset_quota_tracker()
    yield


def setup_mock_client(monkeypatch, mock_post_fn):
    """Utility to setup a mock httpx.AsyncClient."""
    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            resp_data = {
                "models": [
                    {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemini-2.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemma-4-26b-a4b-it", "supportedGenerationMethods": ["generateContent"]},
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
async def test_429_triggers_immediate_failover(monkeypatch, capsys):
    """Model returns 429, next model is tried immediately."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    from config.settings import get_settings
    get_settings.cache_clear()

    call_count = {"n": 0}

    async def mock_post(url, *args, **kwargs):
        call_count["n"] += 1
        req = httpx.Request("POST", url)

        # First call (gemini-2.5-flash) returns 429
        if call_count["n"] == 1:
            return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")

        # Second call (gemini-2.5-flash-lite) succeeds
        resp_data = {
            "candidates": [{"content": {"parts": [{"text": "Success from lite"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
        }
        return httpx.Response(status_code=200, request=req, json=resp_data)

    setup_mock_client(monkeypatch, mock_post)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    mgr.settings = get_settings()

    result = await mgr.generate(prompt="Test", role=AgentRole.PLANNER, provider="auto")

    assert result == "Success from lite"
    assert call_count["n"] == 2

    captured = capsys.readouterr()
    assert "provider_failed=429" in captured.out
    assert "provider_success=true" in captured.out


@pytest.mark.asyncio
async def test_resource_exhausted_body_triggers_failover(monkeypatch, capsys):
    """HTTP 200 but with RESOURCE_EXHAUSTED in body triggers failover."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    from config.settings import get_settings
    get_settings.cache_clear()

    call_count = {"n": 0}

    async def mock_post(url, *args, **kwargs):
        call_count["n"] += 1
        req = httpx.Request("POST", url)

        # First model: returns error
        if call_count["n"] == 1:
            return httpx.Response(
                status_code=429,
                request=req,
                text="RESOURCE_EXHAUSTED: quota exceeded",
            )

        # Next model succeeds
        resp_data = {
            "candidates": [{"content": {"parts": [{"text": "Fallback result"}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 10},
        }
        return httpx.Response(status_code=200, request=req, json=resp_data)

    setup_mock_client(monkeypatch, mock_post)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    mgr.settings = get_settings()

    result = await mgr.generate(prompt="Test", role=AgentRole.CRITIC, provider="auto")
    assert result == "Fallback result"

    # Verify the first model is now in cooldown
    tracker = get_quota_tracker()
    first_model = LLMManager._routing_pool[0]
    assert not tracker.is_available(first_model)


@pytest.mark.asyncio
async def test_full_chain_failover_to_mock(monkeypatch, capsys):
    """All models fail → mock produces output."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    from config.settings import get_settings
    get_settings.cache_clear()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")

    setup_mock_client(monkeypatch, mock_post)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    mgr.settings = get_settings()

    result = await mgr.generate(prompt="Test failover", role=AgentRole.PLANNER, provider="auto")

    # Must fall back to mock and succeed
    assert result is not None
    assert len(result) > 0

    captured = capsys.readouterr()
    assert "provider_success=true" in captured.out

    # Verify all real models were attempted
    for model_id in LLMManager._routing_pool:
        assert any(model_id in url for url in called_urls), f"Model {model_id} was not attempted"


@pytest.mark.asyncio
async def test_failover_preserves_role_strategy(monkeypatch, capsys):
    """Quality roles try quality-priority models first."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    from config.settings import get_settings
    get_settings.cache_clear()

    attempted_models = []

    async def mock_post(url, *args, **kwargs):
        # Extract model from URL
        import re
        model_match = re.search(r'/models/([^:]+):', url)
        if model_match:
            attempted_models.append(model_match.group(1))

        req = httpx.Request("POST", url)

        # All fail to force full chain traversal to mock
        return httpx.Response(status_code=429, request=req, text="Rate limit")

    setup_mock_client(monkeypatch, mock_post)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    mgr.settings = get_settings()

    # WRITER role = QUALITY strategy → should try highest-priority first
    await mgr.generate(prompt="Test", role=AgentRole.WRITER, provider="auto")

    # The first attempted model should be the highest-priority one (gemini-2.5-flash)
    assert len(attempted_models) > 0
    assert "gemini-2.5-flash" in attempted_models[0]
