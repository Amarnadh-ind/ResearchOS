"""
LLM Model Routing Policy
Maps agent roles to specific models for intelligent routing.
Configured for OpenAI API (gpt-4o-mini for cost efficiency).
"""

from dataclasses import dataclass
from enum import Enum


class AgentRole(str, Enum):
    PLANNER = "planner"
    READER = "reader"
    CRITIC = "critic"
    CODER = "coder"
    WORKER = "worker"
    SEARCH = "search"
    BROWSER = "browser"
    CLAIM_EXTRACTOR = "claim_extractor"
    NOVELTY = "novelty"
    CITATION = "citation"
    WRITER = "writer"
    IEEE_FORMATTER = "ieee_formatter"
    HUMANIZER = "humanizer"


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.9
    description: str = ""


# ── Model Routing Table ─────────────────────────────────
# Uses OpenAI models (gpt-4o for quality agents, gpt-4o-mini for lightweight)
MODEL_ROUTING: dict[AgentRole, ModelConfig] = {
    AgentRole.PLANNER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=8192,
        temperature=0.4,
        description="Research planning and decomposition",
    ),
    AgentRole.READER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=8192,
        temperature=0.2,
        description="Document reading and comprehension",
    ),
    AgentRole.CRITIC: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.3,
        description="Evidence critique and verification",
    ),
    AgentRole.CODER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.1,
        description="Code generation and analysis",
    ),
    AgentRole.WORKER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=2048,
        temperature=0.2,
        description="Lightweight processing tasks",
    ),
    AgentRole.SEARCH: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.3,
        description="Search query generation",
    ),
    AgentRole.BROWSER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.2,
        description="Web content extraction",
    ),
    AgentRole.CLAIM_EXTRACTOR: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.1,
        description="Claim identification and extraction",
    ),
    AgentRole.NOVELTY: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.4,
        description="Novelty assessment and gap analysis",
    ),
    AgentRole.CITATION: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.1,
        description="Citation verification and formatting",
    ),
    AgentRole.WRITER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=16384,
        temperature=0.5,
        description="Academic paper composition",
    ),
    AgentRole.IEEE_FORMATTER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=8192,
        temperature=0.1,
        description="IEEE format compliance",
    ),
    AgentRole.HUMANIZER: ModelConfig(
        model_id="gpt-4o-mini",
        max_tokens=8192,
        temperature=0.3,
        description="Humanizing and paraphrasing for plagiarism reduction",
    ),
}


# ── Role-based Model Priorities (Issue 5 Routing) ───────
ROLE_PRIORITY_MODELS: dict[AgentRole, list[str]] = {
    AgentRole.PLANNER: ["openai/gpt-4o-mini", "gpt-4o-mini", "anthropic/claude-3-opus", "openai/gpt-4o"],
    AgentRole.READER: ["openai/gpt-4o-mini", "gpt-4o-mini", "anthropic/claude-3-opus", "openai/gpt-4o"],
    AgentRole.CRITIC: ["openai/gpt-4o", "gpt-4o", "anthropic/claude-3-opus", "openai/gpt-4o-mini"],
    AgentRole.CODER: ["openai/gpt-4o-mini", "gpt-4o-mini", "openai/gpt-4o"],
    AgentRole.WORKER: ["openai/gpt-4o-mini", "gpt-4o-mini", "openai/gpt-4o"],
    AgentRole.SEARCH: ["openai/gpt-4o-mini", "gpt-4o-mini", "anthropic/claude-3-opus", "openai/gpt-4o"],
    AgentRole.BROWSER: ["openai/gpt-4o-mini", "gpt-4o-mini", "openai/gpt-4o"],
    AgentRole.CLAIM_EXTRACTOR: ["openai/gpt-4o", "gpt-4o", "anthropic/claude-3-opus", "openai/gpt-4o-mini"],
    AgentRole.NOVELTY: ["openai/gpt-4o", "gpt-4o", "anthropic/claude-3-opus", "openai/gpt-4o-mini"],
    AgentRole.CITATION: ["openai/gpt-4o-mini", "gpt-4o-mini", "openai/gpt-4o"],
    AgentRole.WRITER: ["openai/gpt-4o", "gpt-4o", "anthropic/claude-3-opus", "openai/gpt-4o-mini"],
    AgentRole.IEEE_FORMATTER: ["openai/gpt-4o", "gpt-4o", "anthropic/claude-3-opus", "openai/gpt-4o-mini"],
    AgentRole.HUMANIZER: ["openai/gpt-4o-mini", "gpt-4o-mini", "gemini-2.0-flash", "openai/gpt-4o"],
}


def get_model_config(role: AgentRole) -> ModelConfig:
    """Get the model configuration for a given agent role."""
    return MODEL_ROUTING[role]


# ── Fallback chain ──────────────────────────────────────
FALLBACK_MODELS: list[str] = [
    "gpt-4o-mini",
    "gpt-3.5-turbo",
]
