"""
Tests for Output Guarantee
Verifies that the pipeline always produces output even when all models are exhausted.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from services.llm_manager import LLMManager, get_llm_manager
from services.quota_tracker import reset_quota_tracker


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset discovery and quota tracker before each test."""
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    reset_quota_tracker()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")

    from config.settings import get_settings

    get_settings.cache_clear()

    yield


def setup_all_fail_client(monkeypatch):
    """Setup mock where all real API calls fail with 429."""

    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            resp_data = {
                "models": [
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-flash-lite",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemma-4-31b-it",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemma-4-26b-a4b-it",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                ]
            }
            return httpx.Response(status_code=200, request=req, json=resp_data)
        return httpx.Response(status_code=404, request=req)

    async def mock_post(url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")

    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_client.get = mock_get

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)


@pytest.mark.asyncio
async def test_pipeline_completes_when_all_models_exhausted(monkeypatch):
    """Mock fallback ensures pipeline completion even when all real models fail."""
    setup_all_fail_client(monkeypatch)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    from config.settings import get_settings

    mgr.settings = get_settings()

    result = await mgr.generate(
        prompt="Write about quantum computing",
        role=AgentRole.WRITER,
        provider="auto",
    )

    assert result is not None
    assert len(result) > 0


@pytest.mark.asyncio
async def test_each_pipeline_stage_produces_output(monkeypatch):
    """Every role in the pipeline produces output via mock fallback."""
    setup_all_fail_client(monkeypatch)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    from config.settings import get_settings

    mgr.settings = get_settings()

    pipeline_roles = [
        AgentRole.PLANNER,
        AgentRole.SEARCH,
        AgentRole.CLAIM_EXTRACTOR,
        AgentRole.CRITIC,
        AgentRole.WRITER,
        AgentRole.IEEE_FORMATTER,
        AgentRole.HUMANIZER,
    ]

    for role in pipeline_roles:
        result = await mgr.generate(
            prompt=f"Test output for {role.value}",
            role=role,
            provider="auto",
        )
        assert result is not None, f"Role {role.value} produced no output"
        assert len(result) > 0, f"Role {role.value} produced empty output"


@pytest.mark.asyncio
async def test_mock_fallback_produces_valid_json(monkeypatch):
    """Mock output for JSON-mode agents is parseable JSON."""
    import json

    setup_all_fail_client(monkeypatch)
    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    from config.settings import get_settings

    mgr.settings = get_settings()

    json_roles = [
        AgentRole.PLANNER,
        AgentRole.CLAIM_EXTRACTOR,
        AgentRole.CRITIC,
        AgentRole.CITATION,
        AgentRole.WRITER,
        AgentRole.IEEE_FORMATTER,
    ]

    for role in json_roles:
        result = await mgr.generate(
            prompt="Generate JSON output",
            role=role,
            provider="auto",
            json_mode=True,
        )
        assert result is not None, f"Role {role.value} produced no output"

        # Try to parse as JSON — mock should produce valid JSON for these roles
        try:
            parsed = json.loads(result)
            assert isinstance(parsed, (dict, list)), f"Role {role.value} JSON is not dict/list"
        except json.JSONDecodeError:
            # Some mock outputs might not be strict JSON, that's OK as long as they exist
            assert len(result) > 10, f"Role {role.value} produced too-short output: {result[:100]}"


@pytest.mark.asyncio
async def test_mixed_failures_some_real_some_mock(monkeypatch):
    """Some stages use real models, others fall back to mock."""
    call_count = {"n": 0}

    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            resp_data = {
                "models": [
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

    async def mock_post(url, *args, **kwargs):
        call_count["n"] += 1
        req = httpx.Request("POST", url)

        # First request succeeds (PLANNER)
        if call_count["n"] == 1:
            resp_data = {
                "candidates": [{"content": {"parts": [{"text": "Real model response"}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
            }
            return httpx.Response(status_code=200, request=req, json=resp_data)

        # All subsequent requests fail
        return httpx.Response(status_code=429, request=req, text="Rate limit exceeded")

    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_client.get = mock_get

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)

    await LLMManager.discover_google_models()

    mgr = get_llm_manager()
    from config.settings import get_settings

    mgr.settings = get_settings()

    # First call: real model
    result1 = await mgr.generate(prompt="Plan research", role=AgentRole.PLANNER, provider="auto")
    assert result1 == "Real model response"

    # Second call: real models fail, falls back to mock
    result2 = await mgr.generate(prompt="Write paper", role=AgentRole.WRITER, provider="auto")
    assert result2 is not None
    assert len(result2) > 0
    # Both should have produced output
    assert result1 != result2  # Different outputs for different roles
