"""
ResearchOS — FastAPI Application
Autonomous Multi-Agent Research Laboratory
"""

import structlog
from contextlib import asynccontextmanager
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
    """Application lifespan — startup and shutdown."""
    settings = get_settings()
    logger.info("researchos_starting", version=settings.app_version)

    # Connect to services (graceful — don't fail if DBs not ready)
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


# ── Create App ───────────────────────────────────────────
app = FastAPI(
    title="ResearchOS",
    description="Autonomous Multi-Agent Research Laboratory",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # Dev mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────
from api.routes.research import router as research_router
from api.routes.agents import router as agents_router
from api.routes.ws import router as ws_router

app.include_router(research_router)
app.include_router(agents_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "ResearchOS",
        "version": "0.1.0",
        "status": "operational",
        "description": "Autonomous Multi-Agent Research Laboratory",
    }


def resolve_diagnostics_model(key: str) -> tuple[str, str] | None:
    """Resolves a frontend diagnostics key to a (model_name, provider) tuple."""
    from services.llm_manager import LLMManager
    if key == "manus":
        return "manus", "manus"
    elif key == "gemma_31b":
        models = [m for m in LLMManager._discovered_gemma_models if "31b" in m.lower()]
        if models:
            return models[0], "gemma"
        return None
    elif key == "gemma_26b":
        models = [m for m in LLMManager._discovered_gemma_models if "26b" in m.lower()]
        if models:
            return models[0], "gemma"
        return None
    elif key == "gemini_flash":
        models = [m for m in LLMManager._discovered_gemini_models if "2.5-flash" in m.lower() and "lite" not in m.lower()]
        if models:
            return models[0], "gemini"
        return None
    elif key == "gemini_flash_lite":
        models = [m for m in LLMManager._discovered_gemini_models if "lite" in m.lower()]
        if models:
            return models[0], "gemini"
        return None
    return None


@app.get("/health")
async def health():
    # Trigger uvicorn reload to pick up new .env settings (updated keys)
    return {"status": "healthy"}


@app.get("/api/diagnostics/providers")
async def provider_diagnostics():
    from services.llm_manager import LLMManager
    if LLMManager._discovered_status["gemini"] == "untested":
        await LLMManager.discover_google_models()
        
    keys = ["manus", "gemma_31b", "gemma_26b", "gemini_flash", "gemini_flash_lite"]
    result = {}
    for key in keys:
        resolved = resolve_diagnostics_model(key)
        if resolved:
            model, prov = resolved
            await LLMManager.test_model_health(prov, model)
            diag = LLMManager._model_diagnostics.get(model, {})
            result[key] = "online" if diag.get("connected") else "offline"
        else:
            result[key] = "offline"
    return result


@app.get("/api/diagnostics/providers/details")
async def provider_diagnostics_details():
    from services.llm_manager import LLMManager
    if LLMManager._discovered_status["gemini"] == "untested":
        await LLMManager.discover_google_models()
        
    keys = ["manus", "gemma_31b", "gemma_26b", "gemini_flash", "gemini_flash_lite"]
    result = {}
    for key in keys:
        display_name = {
            "manus": "Manus AI",
            "gemma_31b": "Gemma 4 31B",
            "gemma_26b": "Gemma 4 26B",
            "gemini_flash": "Gemini Flash",
            "gemini_flash_lite": "Gemini Flash Lite"
        }[key]
        prov = "gemma" if "gemma" in key else ("gemini" if "gemini" in key else "manus")
        
        resolved = resolve_diagnostics_model(key)
        if resolved:
            model, prov = resolved
            await LLMManager.test_model_health(prov, model)
            diag = LLMManager._model_diagnostics.get(model, {})
            result[key] = {
                "status": "online" if diag.get("connected") else "offline",
                "connected": bool(diag.get("connected")),
                "latency": diag.get("latency", 0),
                "last_status": diag.get("last_status", 0),
                "last_error": diag.get("last_error", ""),
                "model_name": model,
                "display_name": display_name,
                "provider": prov
            }
        else:
            status_error = LLMManager._discovered_status.get(prov, "unavailable model")
            if status_error == "online":
                status_error = "unavailable model"
            from config.settings import get_settings
            api_key = getattr(get_settings(), f"{prov}_api_key", "")
            if not api_key:
                status_error = "invalid API key"
                
            result[key] = {
                "status": "offline",
                "connected": False,
                "latency": 0,
                "last_status": 404 if status_error == "unavailable model" else 400,
                "last_error": status_error,
                "model_name": "none",
                "display_name": display_name,
                "provider": prov
            }
    return result


@app.get("/api/diagnostics")
async def system_diagnostics(session_id: str | None = None):
    from config.settings import get_settings
    from memory.session import get_session_memory
    from services.llm_manager import LLMManager, get_llm_manager
    
    mgr = get_llm_manager()
    
    if LLMManager._discovered_status["gemini"] == "untested":
        await LLMManager.discover_google_models()
        
    keys = ["manus", "gemma_31b", "gemma_26b", "gemini_flash", "gemini_flash_lite"]
    for key in keys:
        resolved = resolve_diagnostics_model(key)
        if resolved:
            model, prov = resolved
            await LLMManager.test_model_health(prov, model)
                
    active_prov = "none"
    active_model = "none"
    api_connected = False
    
    for key in keys:
        resolved = resolve_diagnostics_model(key)
        if resolved:
            model, prov = resolved
            diag = LLMManager._model_diagnostics.get(model, {})
            if diag.get("connected"):
                active_prov = prov
                active_model = model
                api_connected = True
                break
            
    last_status_code = 200 if api_connected else 401
    
    total_sources = 0
    citations_found = 0
    
    if session_id:
        try:
            session_mem = get_session_memory()
            state = await session_mem.get_state(session_id)
            if state:
                total_sources = len(state.get("sources", []))
                citations_found = len(state.get("citations", []))
        except Exception:
            pass
            
    provider_details = {}
    for key in keys:
        display_name = {
            "manus": "Manus AI",
            "gemma_31b": "Gemma 4 31B",
            "gemma_26b": "Gemma 4 26B",
            "gemini_flash": "Gemini Flash",
            "gemini_flash_lite": "Gemini Flash Lite"
        }[key]
        prov = "gemma" if "gemma" in key else ("gemini" if "gemini" in key else "manus")
        
        resolved = resolve_diagnostics_model(key)
        if resolved:
            model, prov = resolved
            diag = LLMManager._model_diagnostics.get(model, {})
            provider_details[key] = {
                "status": "online" if diag.get("connected") else "offline",
                "connected": bool(diag.get("connected")),
                "latency": diag.get("latency", 0),
                "last_status": diag.get("last_status", 0),
                "last_error": diag.get("last_error", ""),
                "model_name": model,
                "display_name": display_name,
                "provider": prov
            }
        else:
            status_error = LLMManager._discovered_status.get(prov, "unavailable model")
            if status_error == "online":
                status_error = "unavailable model"
            from config.settings import get_settings
            api_key = getattr(get_settings(), f"{prov}_api_key", "")
            if not api_key:
                status_error = "invalid API key"
                
            provider_details[key] = {
                "status": "offline",
                "connected": False,
                "latency": 0,
                "last_status": 404 if status_error == "unavailable model" else 400,
                "last_error": status_error,
                "model_name": "none",
                "display_name": display_name,
                "provider": prov
            }
            
    return {
        "provider": active_prov,
        "model": active_model,
        "api_connected": api_connected,
        "last_status_code": last_status_code,
        "mock_mode": False,
        "active_pipeline": "real",
        "total_sources": total_sources,
        "citations_found": citations_found,
        "provider_details": provider_details,
    }
