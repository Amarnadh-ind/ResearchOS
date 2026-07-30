"""
ResearchOS Application Settings
Centralized configuration via Pydantic Settings with env var support.
"""

from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────
    app_name: str = "ResearchOS"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "info"
    mock_llm: bool = False

    # ── Backend Server ───────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 4
    cors_origins: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://researchos-frontend.onrender.com",
]
    # ── OpenRouter ───────────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Multi-Provider LLM Keys ──────────────────────────
    manus_api_key: str = ""
    manus_base_url: str = "https://api.manus.im/v1"
    gemma_api_key: str = ""
    gemini_api_key: str = ""
    grok_api_key: str = ""
    openai_api_key: str = ""
    nemotron_api_key: str = ""
    nemotron_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_provider: str = "auto"
    model_cooldown_seconds: int = 120  # 2 minutes default cooldown per model

    # ── Firecrawl ────────────────────────────────────────
    firecrawl_api_key: str = ""
    firecrawl_base_url: str = "https://api.firecrawl.dev/v1"

    # ── Web Search ───────────────────────────────────────
    tavily_api_key: str = ""

    # ── PostgreSQL ───────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "researchos"
    postgres_password: str = "researchos_secret_2024"
    postgres_db: str = "researchos"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    # ── FAST MODE ────────────────────────────────────────
    fast_mode: bool = True
    fast_mode_max_sources: int = 3
    fast_mode_max_claims: int = 5
    fast_mode_max_attempts: int = 1
    fast_mode_skip_humanizer: bool = False
    fast_mode_skip_ieee_llm: bool = False
    fast_mode_writer_max_tokens: int = 8192
    fast_mode_reader_max_chars: int = 4000
    fast_mode_provider_timeout: float = 10.0
    fast_mode_firecrawl_timeout: int = 15000

    # ── Qdrant ───────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection: str = "researchos_documents"

    # ── Neo4j ────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "researchos_neo4j_2024"

    # ── Embedding ────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Global topic variable for pipeline-wide hard topic lock
GLOBAL_RESEARCH_TOPIC: str = "Autonomous Multi-Agent Systems"

import contextvars

active_topic_var = contextvars.ContextVar("active_topic", default="")
active_session_id_var = contextvars.ContextVar("active_session_id", default="")
