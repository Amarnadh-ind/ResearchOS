import pytest


@pytest.fixture(autouse=True)
def clear_api_keys(monkeypatch):
    """Ensure API keys from .env don't interfere with tests."""
    from config.settings import Settings, get_settings

    # Disable loading from .env file during tests
    Settings.model_config["env_file"] = None

    for key in [
        "NEMOTRON_API_KEY",
        "NEMOTRON_BASE_URL",
        "MANUS_API_KEY",
        "MANUS_BASE_URL",
        "GEMINI_API_KEY",
        "GEMMA_API_KEY",
        "GROK_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "TAVILY_API_KEY",
        "FIRECRAWL_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
