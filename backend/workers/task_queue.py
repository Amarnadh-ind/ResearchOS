"""
Background task queue management.
"""

import asyncio
import structlog
from collections import OrderedDict

logger = structlog.get_logger()

# Simple in-memory task tracking (Redis-backed in production)
_task_registry: OrderedDict[str, dict] = OrderedDict()
MAX_TASKS = 100


def register_task(task_id: str, description: str = ""):
    """Register a background task."""
    _task_registry[task_id] = {
        "id": task_id,
        "description": description,
        "status": "running",
    }
    # Evict old tasks
    while len(_task_registry) > MAX_TASKS:
        _task_registry.popitem(last=False)


def complete_task(task_id: str, status: str = "completed"):
    """Mark a task as completed."""
    if task_id in _task_registry:
        _task_registry[task_id]["status"] = status


def get_active_tasks() -> list[dict]:
    """Get all active tasks."""
    return [t for t in _task_registry.values() if t["status"] == "running"]
