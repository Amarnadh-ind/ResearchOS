import sys
import os
import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.llm_manager import get_llm_manager
from config.models import AgentRole
from config.settings import get_settings

def test_llm_manager_chain_resolution():
    from services.llm_manager import LLMManager
    LLMManager._discovered_gemma_models = []
    LLMManager._discovered_gemini_models = []
    LLMManager._discovered_status = {
        "manus": "untested",
        "gemma": "untested",
        "gemini": "untested"
    }

    mgr = get_llm_manager()
    old_provider = mgr.settings.llm_provider
    old_gemma_key = mgr.settings.gemma_api_key
    old_gemini_key = mgr.settings.gemini_api_key
    old_manus_key = mgr.settings.manus_api_key
    
    mgr.settings.llm_provider = "auto"
    mgr.settings.gemma_api_key = "test-gemma-key"
    mgr.settings.gemini_api_key = "test-gemini-key"
    mgr.settings.manus_api_key = ""
    
    try:
        # 1. Default Planner Chain should prioritize Gemma
        planner_chain = mgr._get_provider_chain(AgentRole.PLANNER)
        assert planner_chain[0] == ("gemma", "gemma-4-31b-it")
        assert planner_chain[1] == ("gemma", "gemma-4-26b-a4b-it")
        assert planner_chain[2] == ("gemini", "gemini-2.5-flash")
        assert planner_chain[3] == ("gemini", "gemini-2.5-flash-lite")
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
        mgr.settings.gemma_api_key = old_gemma_key
        mgr.settings.gemini_api_key = old_gemini_key
        mgr.settings.manus_api_key = old_manus_key
