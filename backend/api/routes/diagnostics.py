"""
Diagnostics API Routes
System health, provider status, cooldown dashboard, and PDF diagnostics.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()
router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


def _format_provider_details(telemetry_models: dict) -> dict:
    """Format provider telemetry into detail entries for the dashboard."""
    details = {}
    from services.llm_manager import LLMManager

    compat_map = {
        "gemini-2.5-flash": ("gemini_flash", "Gemini 2.5 Flash", "gemini"),
        "gemini-2.5-flash-lite": ("gemini_flash_lite", "Gemini 2.5 Flash Lite", "gemini"),
        "gemma-4-31b-it": ("gemma_31b", "Gemma 4 31B", "gemma"),
        "gemma-4-26b-a4b-it": ("gemma_26b", "Gemma 4 26B", "gemma"),
        "gemma-4-31b": ("gemma_31b", "Gemma 4 31B", "gemma"),
        "gemma-4-26b": ("gemma_26b", "Gemma 4 26B", "gemma"),
    }

    default_keys = {
        "gemini_flash": ("gemini-2.5-flash", "gemini", "offline"),
        "gemini_flash_lite": ("gemini-2.5-flash-lite", "gemini", "offline"),
        "gemma_31b": ("gemma-4-31b-it", "gemma", "offline"),
        "gemma_26b": ("gemma-4-26b-a4b-it", "gemma", "offline"),
    }

    for k, (model_id, prov, default_status) in default_keys.items():
        details[k] = {
            "status": default_status,
            "connected": False,
            "latency": 0,
            "last_status": 0,
            "last_error": "",
            "model_name": model_id,
            "display_name": k.replace("_", " ").title(),
            "provider": prov,
        }

    merged_models = {}

    for model_id, m in telemetry_models.items():
        status = m.get("status", "offline")
        connected = status == "online"
        merged_models[model_id] = {
            "status": "online" if connected else "offline",
            "connected": connected,
            "latency": m.get("latency_ms", 0),
            "last_status": 200 if connected else (500 if status == "cooldown" else 404),
            "last_error": m.get("last_error", ""),
            "provider": m.get("provider", "gemini"),
        }

    for model_id, diag in LLMManager._model_diagnostics.items():
        connected = diag.get("connected", False)
        merged_models[model_id] = {
            "status": "online" if connected else "offline",
            "connected": connected,
            "latency": diag.get("latency", 0),
            "last_status": diag.get("last_status", 200 if connected else 500),
            "last_error": diag.get("last_error", ""),
            "provider": diag.get("provider", "gemini"),
        }

    for model_id, m in merged_models.items():
        status = m["status"]
        connected = m["connected"]

        detail_entry = {
            "status": status,
            "connected": connected,
            "latency": m["latency"],
            "last_status": m["last_status"],
            "last_error": m["last_error"],
            "model_name": model_id,
            "display_name": model_id,
            "provider": m["provider"],
        }

        details[model_id] = detail_entry

        for cmp_model_id, (compat_key, disp, prov) in compat_map.items():
            is_match = False
            if cmp_model_id == model_id:
                is_match = True
            elif ("lite" not in model_id and "lite" not in cmp_model_id) or \
                    ("lite" in model_id and "lite" in cmp_model_id):
                if (model_id in cmp_model_id) or (cmp_model_id in model_id):
                    is_match = True

            if is_match:
                compat_entry = detail_entry.copy()
                compat_entry["display_name"] = disp
                compat_entry["provider"] = prov
                details[compat_key] = compat_entry

    from services.firecrawl_service import get_firecrawl_service
    firecrawl = get_firecrawl_service()
    details["firecrawl"] = {
        "status": firecrawl.status,
        "connected": firecrawl.status == "online",
        "latency": firecrawl.last_latency,
        "last_status": 200 if firecrawl.status == "online" else 500,
        "last_error": firecrawl.last_error,
        "model_name": "Firecrawl API",
        "display_name": "Firecrawl",
        "provider": "firecrawl",
    }
    return details


@router.get("/providers")
async def provider_diagnostics():
    """Quick status check for all models in the routing pool."""
    from services.llm_manager import LLMManager
    from services.quota_tracker import get_quota_tracker

    if not LLMManager._discovery_completed:
        await LLMManager.discover_google_models()

    tracker = get_quota_tracker()
    telemetry = tracker.get_telemetry()

    details = _format_provider_details(telemetry["models"])
    result = {k: v["status"] for k, v in details.items()}
    return result


@router.get("/providers/details")
async def provider_diagnostics_details():
    """Detailed per-model diagnostics with telemetry."""
    from services.llm_manager import LLMManager
    from services.quota_tracker import get_quota_tracker

    if not LLMManager._discovery_completed:
        await LLMManager.discover_google_models()

    tracker = get_quota_tracker()
    telemetry = tracker.get_telemetry()

    return _format_provider_details(telemetry["models"])


@router.get("/routing-pool")
async def routing_pool():
    """Return the current ordered routing pool with health status."""
    from services.llm_manager import LLMManager
    from services.quota_tracker import get_quota_tracker

    if not LLMManager._discovery_completed:
        await LLMManager.discover_google_models()

    tracker = get_quota_tracker()

    pool = []
    for model_id in LLMManager._routing_pool:
        record = tracker.get_model_record(model_id)
        if record:
            pool.append(record.to_telemetry())

    return {
        "pool": pool,
        "mock_fallback": "always_available",
        "total_models": len(pool),
    }


@router.get("")
async def system_diagnostics(session_id: str | None = None):
    """System-wide diagnostics overview."""
    from services.llm_manager import LLMManager
    from services.quota_tracker import get_quota_tracker

    if not LLMManager._discovery_completed:
        await LLMManager.discover_google_models()

    tracker = get_quota_tracker()
    telemetry = tracker.get_telemetry()

    active_model = "none"
    active_provider = "none"
    api_connected = False

    for model_id in LLMManager._routing_pool:
        record = tracker.get_model_record(model_id)
        diag = LLMManager._model_diagnostics.get(model_id)
        diag_connected = diag.get("connected", True) if diag else True
        if record and record.is_available and diag_connected:
            active_model = model_id
            active_provider = record.provider
            api_connected = True
            break

    total_sources = 0
    citations_found = 0

    if session_id:
        try:
            from memory.session import get_session_memory
            session_mem = get_session_memory()
            state = await session_mem.get_state(session_id)
            if state:
                total_sources = len(state.get("sources", []))
                citations_found = len(state.get("citations", []))
        except Exception:
            pass

    provider_details = _format_provider_details(telemetry["models"])

    return {
        "provider": active_provider,
        "model": active_model,
        "api_connected": api_connected,
        "last_status_code": 200 if api_connected else 401,
        "mock_mode": False,
        "active_pipeline": "real",
        "total_sources": total_sources,
        "citations_found": citations_found,
        "routing_pool": LLMManager._routing_pool,
        "telemetry": telemetry,
        "provider_details": provider_details,
    }


@router.get("/pdf")
async def pdf_diagnostics():
    """PDF generation health check — verifies all renderers and dependencies."""
    from services.pdf_generator import PDFGenerator

    status = PDFGenerator.get_renderer_status()
    playwright_ok = bool(status["playwright"].get("chromium_path"))
    fpdf2_ok = status["fpdf2"]["available"]

    from services.pdf_generator import KATEX_AUTO_INLINE, KATEX_CSS_INLINE, KATEX_JS_INLINE
    katex_ok = bool(KATEX_CSS_INLINE and KATEX_JS_INLINE and KATEX_AUTO_INLINE)

    overall = (
        "healthy" if (playwright_ok or fpdf2_ok)
        else "unhealthy"
    )

    return {
        "status": overall,
        "renderers": status,
        "katex_bundled": katex_ok,
        "offline_capable": playwright_ok and katex_ok,
        "any_renderer_available": playwright_ok or fpdf2_ok,
        "primary_available": playwright_ok,
    }


@router.get("/cooldown")
async def cooldown_dashboard():
    """Provider cooldown dashboard with error classification and recovery info."""
    from services.llm_manager import LLMManager
    from services.quota_tracker import QuotaTracker, get_quota_tracker

    if not LLMManager._discovery_completed:
        await LLMManager.discover_google_models()

    tracker = get_quota_tracker()
    telemetry = tracker.get_telemetry()

    models_status = []
    now = datetime.utcnow()

    for model_id, m in telemetry["models"].items():
        record = tracker.get_model_record(model_id)

        status = m.get("status", "offline")
        connected = status == "online"
        cooldown_remaining = m.get("cooldown_remaining_s", 0)

        last_error = m.get("last_error", "")
        last_status = m.get("last_status", 0)
        error_class = QuotaTracker.classify_error(last_error, last_status)

        recovery = QuotaTracker.get_recovery_info(record, cooldown_remaining)

        models_status.append({
            "model": model_id,
            "provider": m.get("provider", "unknown"),
            "priority": m.get("priority", 999),
            "status": status,
            "connected": connected,
            "latency_ms": m.get("latency_ms", 0),
            "requests_made": m.get("requests_used", 0),
            "cooldown_remaining_s": cooldown_remaining,
            "consecutive_failures": m.get("consecutive_failures", 0),
            "last_error": last_error[:200],
            "last_status_code": last_status,
            "error_class": error_class,
            "recovery": recovery,
            "last_success": m.get("last_success"),
        })

    online_count = sum(1 for m in models_status if m["connected"])
    cooldown_count = sum(1 for m in models_status if m["status"] == "cooldown")
    unavailable_count = sum(1 for m in models_status if m["status"] == "unavailable")

    return {
        "timestamp": now.isoformat(),
        "summary": {
            "total": len(models_status),
            "online": online_count,
            "cooldown": cooldown_count,
            "unavailable": unavailable_count,
            "mock_fallback": "always_available",
        },
        "models": sorted(models_status, key=lambda x: (x["priority"], x["model"])),
        "routing_pool": LLMManager._routing_pool,
        "error_classes": {
            "quota_exceeded": "Rate limit / quota exhausted - auto-recovers after cooldown",
            "invalid_key": "Authentication failure - check API keys, won't auto-recover",
            "unavailable_model": "Model not found or not supported - won't auto-recover",
            "network_error": "Transient network failure - retries with backoff",
            "service_overloaded": "Provider overloaded (503) - medium cooldown",
            "permanent_failure": "Model incompatible with required features - permanently excluded",
            "unknown": "Unclassified error - short cooldown after 3 failures",
        },
    }
