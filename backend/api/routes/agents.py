"""
Agent Status API Routes
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/status")
async def get_agents_status():
    """Get status of all agents in the system."""
    from config.models import MODEL_ROUTING, AgentRole

    agents = []
    for role in AgentRole:
        config = MODEL_ROUTING[role]
        agents.append(
            {
                "name": role.value,
                "model": config.model_id,
                "description": config.description,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
        )

    return {"agents": agents}


@router.get("/pipeline")
async def get_pipeline_info():
    """Get the pipeline structure."""
    return {
        "pipeline": [
            {"order": 1, "agent": "planner", "description": "Decomposes research prompt into plan"},
            {"order": 2, "agent": "search", "description": "Searches the web for relevant sources"},
            {
                "order": 3,
                "agent": "firecrawl_extract",
                "description": "Extracts clean markdown via Firecrawl",
            },
            {"order": 4, "agent": "reader", "description": "Deeply reads and structures documents"},
            {"order": 5, "agent": "claim_extractor", "description": "Extracts verifiable claims"},
            {"order": 6, "agent": "critic", "description": "Critiques evidence quality"},
            {"order": 7, "agent": "novelty", "description": "Assesses research novelty"},
            {"order": 8, "agent": "citation", "description": "Verifies and formats citations"},
            {"order": 9, "agent": "writer", "description": "Composes the academic paper"},
            {"order": 10, "agent": "ieee_formatter", "description": "Formats to IEEE standard"},
        ]
    }
