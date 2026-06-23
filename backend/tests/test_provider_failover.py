"""
Tests for Provider Failover Chain
Updated to use the new QuotaTracker-based routing system.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from config.settings import get_settings
from services.llm_manager import LLMManager, get_llm_manager
from services.quota_tracker import reset_quota_tracker


@pytest.fixture(autouse=True)
def clean_discovery():
    """Reset the discovered status, routing pool, and quota tracker before each test."""
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    reset_quota_tracker()


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
                    {"name": "models/gemini-2.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
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
async def test_full_failover_chain_all_models_to_mock(monkeypatch, capsys):
    """All real models fail with 429 → falls back to mock successfully."""
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

    called_urls = []

    async def mock_post(url, *args, **kwargs):
        called_urls.append(url)
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()

    res = await mgr.generate(
        prompt="Test failover",
        role=AgentRole.PLANNER,
        provider="auto",
    )

    # Must fall back to mock and succeed
    assert res is not None
    assert len(res) > 0

    # Verify all discovered models were attempted
    assert any("gemini-2.5-flash" in url for url in called_urls)
    assert any("gemini-2.5-flash-lite" in url for url in called_urls)
    assert any("gemma-4-31b-it" in url for url in called_urls)
    assert any("gemma-4-26b-a4b-it" in url for url in called_urls)

    captured = capsys.readouterr()
    stdout = captured.out

    assert "provider_failed=429" in stdout
    assert "provider_success=true" in stdout


@pytest.mark.asyncio
async def test_missing_keys_routing(monkeypatch, capsys):
    """With only GEMINI key, GEMMA models are skipped."""
    monkeypatch.setenv("GEMMA_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    get_settings.cache_clear()
    mgr = get_llm_manager()
    mgr.settings = get_settings()

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
                "candidatesTokenCount": 20,
            },
        }
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=200, request=req, json=resp_data)

    setup_mock_client(monkeypatch, mock_post)
    await mgr.discover_google_models()

    res = await mgr.generate(
        prompt="Test missing key",
        role=AgentRole.PLANNER,
        provider="auto",
    )

    assert res == "Gemini direct response"
    # First successful call should be to a gemini model
    assert len(called_urls) >= 1
    assert "gemini" in called_urls[0].lower()

    captured = capsys.readouterr()
    stdout = captured.out
    assert "provider_success=true" in stdout
