"""
ResearchOS  FastAPI Application
Autonomous Multi-Agent Research Laboratory
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan  startup and shutdown."""
    settings = get_settings()
    logger.info("researchos_starting", version=settings.app_version)

    # Connect to services (graceful  don't fail if DBs not ready)
    try:
        from services.llm_manager import LLMManager

        await LLMManager.verify_startup_health()
    except Exception as e:
        logger.error("failed_llm_startup_validation", error=str(e))

    try:
        from memory.session import get_session_memory

        await get_session_memory().connect()
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    # Clean up stuck transient sessions from previous runs
    try:
        from memory.metadata import get_metadata_store

        metadata = get_metadata_store()
        active_ids = await metadata.get_active_session_ids()
        if active_ids:
            logger.info("cleaning_up_stuck_sessions", count=len(active_ids), session_ids=active_ids)
            from memory.session import get_session_memory

            session_mem = get_session_memory()
            for sid in active_ids:
                # Mark failed in metadata DB
                await metadata.update_session_status(
                    sid, "failed", error="Pipeline aborted due to server restart."
                )
                # Mark failed in Redis state
                await session_mem.set_state(
                    sid, {"status": "failed", "error": "Pipeline aborted due to server restart."}
                )
    except Exception as e:
        logger.warning("failed_stuck_session_cleanup", error=str(e))

    try:
        from memory.retrieval_mem import get_retrieval_memory

        await get_retrieval_memory().connect()
    except Exception as e:
        logger.warning("qdrant_unavailable", error=str(e))

    try:
        from memory.knowledge_graph import get_knowledge_graph

        await get_knowledge_graph().connect()
    except Exception as e:
        logger.warning("neo4j_unavailable", error=str(e))

    logger.info("researchos_ready")

    yield

    # Shutdown
    logger.info("researchos_shutting_down")

    try:
        from services.llm import get_llm_client

        await get_llm_client().close()
    except Exception:
        pass

    try:
        from services.browser_service import get_browser_service

        await get_browser_service().stop()
    except Exception:
        pass

    try:
        from memory.session import get_session_memory

        await get_session_memory().disconnect()
    except Exception:
        pass

    try:
        from memory.retrieval_mem import get_retrieval_memory

        await get_retrieval_memory().disconnect()
    except Exception:
        pass

    try:
        from memory.knowledge_graph import get_knowledge_graph

        await get_knowledge_graph().disconnect()
    except Exception:
        pass

    try:
        from memory.metadata import get_metadata_store

        await get_metadata_store().disconnect()
    except Exception:
        pass


#  Create App
app = FastAPI(
    title="ResearchOS",
    description="Autonomous Multi-Agent Research Laboratory",
    version="0.1.0",
    lifespan=lifespan,
)

#  CORS
settings = get_settings()
cors_origins = list(settings.cors_origins)
if settings.debug:
    cors_origins.append("*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Routes
from api.routes.agents import router as agents_router
from api.routes.diagnostics import router as diagnostics_router
from api.routes.research import router as research_router
from api.routes.ws import router as ws_router

app.include_router(research_router)
app.include_router(agents_router)
app.include_router(ws_router)
app.include_router(diagnostics_router)


@app.get("/")
async def root():
    return {
        "name": "ResearchOS",
        "version": "0.1.0",
        "status": "operational",
        "description": "Autonomous Multi-Agent Research Laboratory",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


def _format_provider_details(telemetry_models: dict) -> dict:
    """Delegate to diagnostics router for backward compatibility."""
    from api.routes.diagnostics import _format_provider_details as _fmt

    return _fmt(telemetry_models)


def classify_error(error_msg: str, status_code: int) -> str:
    """Classify error into actionable categories."""
    from services.quota_tracker import QuotaTracker

    return QuotaTracker.classify_error(error_msg, status_code)


def get_recovery_info(record, cooldown_remaining: int) -> dict:
    """Generate recovery information for a model."""
    from services.quota_tracker import QuotaTracker

    return QuotaTracker.get_recovery_info(record, cooldown_remaining)
