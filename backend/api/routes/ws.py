"""
WebSocket endpoint for real-time research updates.
Sends previews to the activity stream — full responses stay in backend storage.
"""

import asyncio
import json
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from memory.session import get_session_memory

logger = structlog.get_logger()
router = APIRouter()

# Connected clients per session
_connections: dict[str, list[WebSocket]] = {}

# ── Preview helper ──────────────────────────────────────
PREVIEW_LIMIT = 250
ACTIVITY_MESSAGE_LIMIT = 300

# Keys that contain large payloads — strip from activity events
LARGE_PAYLOAD_KEYS = {"prompt", "response", "raw_llm_output", "content", "content_markdown", "writer_prompt"}

# Keys that are metadata — keep as-is in activity events
METADATA_KEYS = {
    "provider", "model", "tokens_in", "tokens_out", "token_count",
    "cost", "latency", "latency_ms", "response_length", "status",
    "topic", "agent", "type", "error", "duration_ms",
    "total_claims", "total_results", "queries_executed",
    "novelty_score", "overall_evidence_quality",
}


def preview(text: str | None, limit: int = PREVIEW_LIMIT) -> str:
    """Return a short preview of text for activity display."""
    if not text:
        return ""
    return text[:limit] + "..." if len(text) > limit else text


def strip_event_for_activity(event: dict) -> dict:
    """Strip large payloads from an event, keeping only metadata + previews.
    
    Full content is stored in backend and accessible via 
    Sources, Paper, and Diagnostics tabs.
    """
    if not isinstance(event, dict):
        return event

    result = {}
    data = event.get("data", {})

    # Copy top-level non-data fields
    for k, v in event.items():
        if k != "data":
            result[k] = v

    if not isinstance(data, dict):
        result["data"] = data
        return result

    stripped_data = {}
    for key, value in data.items():
        if key in LARGE_PAYLOAD_KEYS and isinstance(value, str):
            # Replace with preview only
            stripped_data[f"{key}_preview"] = preview(value, ACTIVITY_MESSAGE_LIMIT)
            stripped_data[f"{key}_length"] = len(value)
        elif key in METADATA_KEYS:
            stripped_data[key] = value
        elif isinstance(value, str) and len(value) > ACTIVITY_MESSAGE_LIMIT:
            # Any other long strings: truncate
            stripped_data[key] = preview(value, ACTIVITY_MESSAGE_LIMIT)
        elif isinstance(value, dict):
            # Nested objects: include summary, not full content
            serialized = json.dumps(value, default=str)
            if len(serialized) > ACTIVITY_MESSAGE_LIMIT:
                stripped_data[key] = {"_preview": f"[Object: {len(value)} keys]", "_size": len(serialized)}
            else:
                stripped_data[key] = value
        elif isinstance(value, list):
            if key in {"results", "sources", "citations"}:
                # Keep the list structure but truncate nested strings to protect activity payload size
                stripped_list = []
                for item in value:
                    if isinstance(item, dict):
                        stripped_item = {}
                        for k, v in item.items():
                            if isinstance(v, str) and len(v) > ACTIVITY_MESSAGE_LIMIT:
                                stripped_item[k] = preview(v, ACTIVITY_MESSAGE_LIMIT)
                            else:
                                stripped_item[k] = v
                        stripped_list.append(stripped_item)
                    elif isinstance(item, str) and len(item) > ACTIVITY_MESSAGE_LIMIT:
                        stripped_list.append(preview(item, ACTIVITY_MESSAGE_LIMIT))
                    else:
                        stripped_list.append(item)
                stripped_data[key] = stripped_list
            elif len(value) > 5:
                stripped_data[key] = {"_preview": f"[Array: {len(value)} items]", "_count": len(value)}
            else:
                stripped_data[key] = value
        else:
            stripped_data[key] = value

    result["data"] = stripped_data
    return result


@router.websocket("/ws/research/{session_id}")
async def research_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live research updates.
    
    Events sent to the activity stream are stripped of large payloads.
    Full responses remain in backend storage (Redis/Postgres) and
    are accessible via the Sources, Paper, and Diagnostics tabs.
    """
    await websocket.accept()

    if session_id not in _connections:
        _connections[session_id] = []
    _connections[session_id].append(websocket)

    logger.info("ws_connected", session_id=session_id)

    session_mem = get_session_memory()
    last_event_idx = 0

    try:
        while True:
            # Poll for new events
            events = await session_mem.get_events(session_id, start=last_event_idx)
            state = await session_mem.get_state(session_id)

            if events:
                for event in events:
                    # Strip large payloads before sending to frontend
                    activity_event = strip_event_for_activity(event)
                    await websocket.send_json({
                        "type": "agent_event",
                        "data": activity_event,
                    })
                last_event_idx += len(events)

            if state:
                # Strip state too — never send full paper body over WS
                stripped_state = {}
                for k, v in state.items():
                    if k in LARGE_PAYLOAD_KEYS:
                        continue  # Skip full content fields
                    elif isinstance(v, str) and len(v) > ACTIVITY_MESSAGE_LIMIT:
                        stripped_state[k] = preview(v, ACTIVITY_MESSAGE_LIMIT)
                    else:
                        stripped_state[k] = v

                await websocket.send_json({
                    "type": "status",
                    "data": stripped_state,
                })

                # Check if completed or failed
                if state.get("status") in ("completed", "failed"):
                    await websocket.send_json({
                        "type": "pipeline_complete",
                        "data": stripped_state,
                    })
                    break

            await asyncio.sleep(1)  # Poll interval

    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("ws_error", session_id=session_id, error=str(e))
    finally:
        if session_id in _connections:
            _connections[session_id].remove(websocket)
            if not _connections[session_id]:
                del _connections[session_id]
