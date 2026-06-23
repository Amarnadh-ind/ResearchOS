import os
import sys

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.models import AgentRole
from services.llm_manager import LLMManager, get_llm_manager


@pytest.fixture(autouse=True)
def clean_tracker():
    from services.llm_manager import LLMManager
    from services.quota_tracker import reset_quota_tracker
    reset_quota_tracker()
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_other_models = []
    LLMManager._routing_pool = []
    LLMManager._discovery_completed = False
    LLMManager._model_diagnostics = {}
    LLMManager._discovered_status = {
        "manus": "untested",
        "gemma": "untested",
        "gemini": "untested"
    }

def test_llm_manager_chain_resolution(monkeypatch):
    # Set environment variables for the test
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-gemma-key")
    monkeypatch.setenv("MANUS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    
    from config.settings import get_settings
    get_settings.cache_clear()
    
    mgr = get_llm_manager()
    old_provider = mgr.settings.llm_provider
    
    mgr.settings.llm_provider = "auto"
    
    try:
        # Re-build routing pool with the new keys
        LLMManager._build_routing_pool()
        
        # 1. Default Planner Chain should prioritize Gemini (under current priority patterns)
        planner_chain = mgr._get_provider_chain(AgentRole.PLANNER)
        assert planner_chain[0] == ("gemini", "gemini-2.5-flash")
        assert planner_chain[1] == ("gemini", "gemini-2.5-flash-lite")
        assert planner_chain[2] == ("gemma", "gemma-4-31b-it")
        assert planner_chain[3] == ("gemma", "gemma-4-26b-a4b-it")
        assert planner_chain[4] == ("mock", "mock-fallback")
        
        # 2. Preferred provider override for Gemini should only include Gemini models + mock-fallback
        gemini_chain = mgr._get_provider_chain(AgentRole.PLANNER, preferred_provider="gemini")
        assert gemini_chain[0] == ("gemini", "gemini-2.5-flash")
        assert gemini_chain[1] == ("gemini", "gemini-2.5-flash-lite")
        assert gemini_chain[2] == ("mock", "mock-fallback")
        assert len(gemini_chain) == 3
        
        # 3. Preferred provider override for Gemma should only include Gemma models + mock-fallback
        gemma_chain = mgr._get_provider_chain(AgentRole.PLANNER, preferred_provider="gemma")
        assert gemma_chain[0] == ("gemma", "gemma-4-31b-it")
        assert gemma_chain[1] == ("gemma", "gemma-4-26b-a4b-it")
        assert gemma_chain[2] == ("mock", "mock-fallback")
        assert len(gemma_chain) == 3
        
        # 4. Preferred provider override for Mock should only include Mock fallback
        mock_chain = mgr._get_provider_chain(AgentRole.PLANNER, preferred_provider="mock")
        assert mock_chain[0] == ("mock", "mock-fallback")
        assert len(mock_chain) == 1
    finally:
        mgr.settings.llm_provider = old_provider
        get_settings.cache_clear()
