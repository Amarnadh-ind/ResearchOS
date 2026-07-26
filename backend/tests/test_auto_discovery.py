"""
Tests for Dynamic Model Auto-Discovery
Verifies that the routing pool is built from discovered models using pattern matching,
not hardcoded model names.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import DEFAULT_MODEL_PRIORITY, compute_model_priority
from services.llm_manager import LLMManager
from services.quota_tracker import get_quota_tracker, reset_quota_tracker


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset everything before each test."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
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
    reset_quota_tracker()
    yield


def make_mock_client(monkeypatch, models_list):
    """Create mock httpx.AsyncClient that returns specified model list."""

    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "models" in url:
            return httpx.Response(status_code=200, request=req, json={"models": models_list})
        return httpx.Response(status_code=404, request=req)

    async def mock_post(url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=429, request=req, text="Rate limit")

    mock_client = MagicMock()
    mock_client.get = mock_get
    mock_client.post = mock_post

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)


@pytest.mark.asyncio
async def test_discovery_builds_priority_pool(monkeypatch):
    """Discovered models are sorted by preference in the routing pool."""
    models = [
        {"name": "models/gemma-4-26b-a4b-it", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]},
    ]
    make_mock_client(monkeypatch, models)

    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    assert len(pool) == 4

    # Priority order: gemini-2.5-flash(10) → gemini-2.5-flash-lite(20) → gemma-4-31b(30) → gemma-4-26b(40)
    assert pool[0] == "gemini-2.5-flash"
    assert pool[1] == "gemini-2.5-flash-lite"
    assert "31b" in pool[2]
    assert "26b" in pool[3]


@pytest.mark.asyncio
async def test_discovery_filters_non_generateContent(monkeypatch):
    """Models without generateContent are excluded from the routing pool."""
    models = [
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-embedding", "supportedGenerationMethods": ["embedContent"]},
        {
            "name": "models/gemma-4-31b-it",
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
    ]
    make_mock_client(monkeypatch, models)

    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    assert len(pool) == 2
    assert "gemini-2.5-flash" in pool
    assert "gemma-4-31b-it" in pool
    assert "gemini-embedding" not in pool


@pytest.mark.asyncio
async def test_no_hardcoded_model_names(monkeypatch):
    """Routing works with completely novel model names (no hardcoding)."""
    models = [
        {"name": "models/gemini-4.0-ultra-pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemma-5-64b-alpha", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-nano-v2", "supportedGenerationMethods": ["generateContent"]},
    ]
    make_mock_client(monkeypatch, models)

    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    # All 3 should be in pool even though they don't match any priority pattern
    assert len(pool) == 3

    # They should all get DEFAULT_MODEL_PRIORITY
    tracker = get_quota_tracker()
    for model_id in pool:
        record = tracker.get_model_record(model_id)
        assert record is not None
        assert record.priority == DEFAULT_MODEL_PRIORITY


@pytest.mark.asyncio
async def test_discovery_failure_uses_defaults(monkeypatch):
    """When ListModels API fails, default models are used."""

    async def mock_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(status_code=500, request=req, text="Internal error")

    async def mock_post(url, *args, **kwargs):
        req = httpx.Request("POST", url)
        return httpx.Response(status_code=500, request=req, text="Error")

    mock_client = MagicMock()
    mock_client.get = mock_get
    mock_client.post = mock_post

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_async_client)

    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    # Should have defaults: gemini-2.5-flash, gemini-2.5-flash-lite, gemma-4-31b-it, gemma-4-26b-a4b-it
    assert len(pool) >= 4
    assert "gemini-2.5-flash" in pool
    assert "gemini-2.5-flash-lite" in pool


def test_compute_model_priority_pattern_matching():
    """Priority computation uses pattern matching, not exact string matching."""
    # Known patterns
    assert compute_model_priority("gemini-2.5-flash") == 10
    assert compute_model_priority("gemini-2.5-flash-lite") == 20
    assert compute_model_priority("gemma-4-31b-it") == 30
    assert compute_model_priority("gemma-4-26b-a4b-it") == 40

    # Variations should still match patterns
    assert compute_model_priority("gemini-2.5-flash-preview-0514") == 10
    assert compute_model_priority("gemini-2.0-flash") == 60

    # Unknown models get default
    assert compute_model_priority("totally-new-model") == DEFAULT_MODEL_PRIORITY


@pytest.mark.asyncio
async def test_discovery_with_many_models(monkeypatch):
    """Large discovery response is handled correctly."""
    models = []
    for i in range(50):
        models.append(
            {
                "name": f"models/experimental-model-{i}",
                "supportedGenerationMethods": ["generateContent"],
            }
        )
    # Add some real-ish ones
    models.append(
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]}
    )
    models.append(
        {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]}
    )

    make_mock_client(monkeypatch, models)
    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    # All models should be in the pool (50 other + 1 gemini + 1 gemma)
    assert len(pool) == 52

    # High-priority models should be first
    assert pool[0] == "gemini-2.5-flash"
    # gemma-4-31b-it should be second (priority 30)
    assert "gemma-4-31b" in pool[1]


@pytest.mark.asyncio
async def test_discovery_excludes_incompatible_models(monkeypatch):
    """Models incompatible with system instructions / JSON mode are excluded."""
    from config.models import EXCLUDED_MODEL_PATTERNS

    models = [
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
        {
            "name": "models/gemini-3.1-flash-tts-preview",
            "supportedGenerationMethods": ["generateContent"],
        },
        {
            "name": "models/gemini-3.1-flash-image",
            "supportedGenerationMethods": ["generateContent"],
        },
        {"name": "models/gemini-embedding", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]},
    ]
    make_mock_client(monkeypatch, models)

    await LLMManager.discover_google_models()

    pool = LLMManager._routing_pool
    # Only compatible models should be in pool
    assert "gemini-2.5-flash" in pool
    assert "gemma-4-31b-it" in pool
    assert "gemini-3.1-flash-tts-preview" not in pool
    assert "gemini-3.1-flash-image" not in pool
    assert "gemini-embedding" not in pool

    # Verify all pooled models pass exclusion check
    for model_id in pool:
        excluded = any(p in model_id.lower() for p in EXCLUDED_MODEL_PATTERNS)
        assert not excluded, f"Model {model_id} should have been excluded"
