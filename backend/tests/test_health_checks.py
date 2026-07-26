import os
import sys
from unittest.mock import patch

import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from main import app
from services.llm_manager import LLMManager

client = TestClient(app)


@pytest.fixture
def mock_health_check(monkeypatch):
    """Mock test_model_health to prevent real network requests."""
    from services.quota_tracker import reset_quota_tracker

    reset_quota_tracker()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMMA_API_KEY", "test-key")
    monkeypatch.setenv("MANUS_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "")

    from config.settings import get_settings

    get_settings.cache_clear()

    LLMManager._discovered_gemma_models = ["gemma-4-31b", "gemma-4-26b"]
    LLMManager._discovered_gemini_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    LLMManager._discovered_other_models = []
    LLMManager._discovery_completed = True
    LLMManager._model_diagnostics = {}
    LLMManager._build_routing_pool()

    LLMManager._discovered_status = {"gemini": "online", "gemma": "online", "manus": "online"}

    # Synchronously populate diagnostics for endpoints to query directly
    for model in ["gemma-4-31b", "gemma-4-26b", "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
        is_online = model in ("gemma-4-31b", "gemini-2.5-flash")
        prov = "gemma" if "gemma" in model else "gemini"
        LLMManager._model_diagnostics[model] = {
            "connected": is_online,
            "latency": 120 if is_online else 0,
            "last_status": 200 if is_online else 500,
            "last_error": "" if is_online else "Simulated failure",
            "provider": prov,
        }

    async def mock_health(provider, model):
        is_online = model in ("gemma-4-31b", "gemini-2.5-flash")
        return is_online

    with patch.object(LLMManager, "test_model_health", side_effect=mock_health) as mock:
        yield mock


def test_diagnostics_providers_endpoint(mock_health_check):
    response = client.get("/api/diagnostics/providers")
    assert response.status_code == 200

    data = response.json()
    # Verify strict schema
    assert "gemma_31b" in data
    assert "gemma_26b" in data
    assert "gemini_flash" in data
    assert "gemini_flash_lite" in data

    # Check expected mocked values
    assert data["gemma_31b"] == "online"
    assert data["gemma_26b"] == "offline"
    assert data["gemini_flash"] == "online"
    assert data["gemini_flash_lite"] == "offline"


def test_diagnostics_providers_details_endpoint(mock_health_check):
    response = client.get("/api/diagnostics/providers/details")
    assert response.status_code == 200

    data = response.json()
    # Verify detailed schema
    for key in ("gemma_31b", "gemma_26b", "gemini_flash", "gemini_flash_lite"):
        assert key in data
        details = data[key]
        assert "status" in details
        assert "connected" in details
        assert "latency" in details
        assert "last_status" in details
        assert "last_error" in details
        assert "model_name" in details
        assert "display_name" in details
        assert "provider" in details

    # Check expected details values
    assert data["gemma_31b"]["status"] == "online"
    assert data["gemma_31b"]["connected"] is True
    assert data["gemma_31b"]["latency"] == 120
    assert data["gemma_31b"]["model_name"] == "gemma-4-31b"
    assert data["gemma_31b"]["display_name"] == "Gemma 4 31B"
    assert data["gemma_31b"]["provider"] == "gemma"

    assert data["gemma_26b"]["status"] == "offline"
    assert data["gemma_26b"]["connected"] is False
    assert data["gemma_26b"]["last_status"] == 500
    assert data["gemma_26b"]["last_error"] == "Simulated failure"


def test_system_diagnostics_endpoint(mock_health_check):
    response = client.get("/api/diagnostics")
    assert response.status_code == 200

    data = response.json()
    # Verify details aggregated inside main diagnostics
    assert "provider" in data
    assert "model" in data
    assert "api_connected" in data
    assert "provider_details" in data

    # Since gemini-2.5-flash (P10) is the highest priority online model, it should show as active provider/model
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-2.5-flash"
    assert data["api_connected"] is True

    provider_details = data["provider_details"]
    assert provider_details["gemma_31b"]["status"] == "online"
    assert provider_details["gemma_26b"]["status"] == "offline"
