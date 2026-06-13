import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm import get_llm_client
from services.llm_manager import get_llm_manager
from config.models import AgentRole

@pytest.mark.asyncio
async def test_mock_mode_active_when_enabled(monkeypatch):
    # Enable MOCK_LLM in environment
    monkeypatch.setenv("MOCK_LLM", "True")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    mgr = get_llm_manager()
    mgr.settings = get_settings()
    
    client = get_llm_client()
    
    # Run complete and verify it returns a mock response
    res = await client.complete(
        role=AgentRole.WRITER,
        system_prompt="Test system prompt",
        user_prompt="Test user prompt on Autonomous Multi-Agent Systems"
    )
    
    assert len(res) > 0
    # Verify it's a mock completion and not a network failure
    assert "Autonomous Multi-Agent Systems" in res or "AI-Based" in res or "Evolution" in res or "Draft" in res

@pytest.mark.asyncio
async def test_mock_fallback_active_when_api_fails(monkeypatch):
    # Enable MOCK_LLM so fallback is permitted
    monkeypatch.setenv("MOCK_LLM", "True")
    # Empty API keys to force failure/skips of real API
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    mgr = get_llm_manager()
    mgr.settings = get_settings()
    
    client = get_llm_client()
    
    # We expect the generate call to fall back to mock since MOCK_LLM=True
    res = await client.complete(
        role=AgentRole.WRITER,
        system_prompt="Test system prompt",
        user_prompt="Test user prompt on Autonomous Multi-Agent Systems"
    )
    
    assert len(res) > 0
    assert "Autonomous Multi-Agent Systems" in res or "AI-Based" in res or "Evolution" in res or "Draft" in res
