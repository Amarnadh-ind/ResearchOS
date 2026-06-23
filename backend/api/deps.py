"""
Dependency injection for API routes.
"""

from config.settings import Settings, get_settings
from memory.metadata import MetadataStore, get_metadata_store
from memory.session import SessionMemory, get_session_memory
from services.llm import LLMClient, get_llm_client


def get_settings_dep() -> Settings:
    return get_settings()


def get_llm_dep() -> LLMClient:
    return get_llm_client()


def get_session_memory_dep() -> SessionMemory:
    return get_session_memory()


def get_metadata_dep() -> MetadataStore:
    return get_metadata_store()
