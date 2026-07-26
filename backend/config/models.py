"""
LLM Model Routing Policy
Maps agent roles to routing strategies for intelligent quota-aware model selection.
"""

from dataclasses import dataclass

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):  # noqa: UP042
        pass


class AgentRole(StrEnum):
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


class ModelStrategy(StrEnum):
    """Routing strategy for model selection."""

    FAST = "fast"  # Lowest latency healthy model
    QUALITY = "quality"  # Highest priority (best) healthy model


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.9
    description: str = ""


# ── Model Routing Table ─────────────────────────────────
# Default configs per role (used for temperature/max_tokens, model_id is
# overridden by the quota-aware router at runtime)
MODEL_ROUTING: dict[AgentRole, ModelConfig] = {
    AgentRole.PLANNER: ModelConfig(
        model_id="auto",
        max_tokens=8192,
        temperature=0.4,
        description="Research planning and decomposition",
    ),
    AgentRole.READER: ModelConfig(
        model_id="auto",
        max_tokens=8192,
        temperature=0.2,
        description="Document reading and comprehension",
    ),
    AgentRole.CRITIC: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.3,
        description="Evidence critique and verification",
    ),
    AgentRole.CODER: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.1,
        description="Code generation and analysis",
    ),
    AgentRole.WORKER: ModelConfig(
        model_id="auto",
        max_tokens=2048,
        temperature=0.2,
        description="Lightweight processing tasks",
    ),
    AgentRole.SEARCH: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.3,
        description="Search query generation",
    ),
    AgentRole.BROWSER: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.2,
        description="Web content extraction",
    ),
    AgentRole.CLAIM_EXTRACTOR: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.1,
        description="Claim identification and extraction",
    ),
    AgentRole.NOVELTY: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.4,
        description="Novelty assessment and gap analysis",
    ),
    AgentRole.CITATION: ModelConfig(
        model_id="auto",
        max_tokens=4096,
        temperature=0.1,
        description="Citation verification and formatting",
    ),
    AgentRole.WRITER: ModelConfig(
        model_id="auto",
        max_tokens=16384,
        temperature=0.5,
        description="Academic paper composition",
    ),
    AgentRole.IEEE_FORMATTER: ModelConfig(
        model_id="auto",
        max_tokens=8192,
        temperature=0.1,
        description="IEEE format compliance",
    ),
    AgentRole.HUMANIZER: ModelConfig(
        model_id="auto",
        max_tokens=8192,
        temperature=0.3,
        description="Humanizing and paraphrasing for plagiarism reduction",
    ),
}


# ── Role-based Routing Strategy ──────────────────────────
# Maps each agent role to a routing strategy:
#   FAST   = lowest latency healthy model (for speed-sensitive stages)
#   QUALITY = highest priority healthy model (for accuracy-critical stages)
ROLE_STRATEGY_MAP: dict[AgentRole, ModelStrategy] = {
    AgentRole.PLANNER: ModelStrategy.FAST,
    AgentRole.SEARCH: ModelStrategy.FAST,
    AgentRole.READER: ModelStrategy.FAST,
    AgentRole.BROWSER: ModelStrategy.FAST,
    AgentRole.CLAIM_EXTRACTOR: ModelStrategy.QUALITY,
    AgentRole.CRITIC: ModelStrategy.QUALITY,
    AgentRole.NOVELTY: ModelStrategy.QUALITY,
    AgentRole.CITATION: ModelStrategy.QUALITY,
    AgentRole.WRITER: ModelStrategy.QUALITY,
    AgentRole.IEEE_FORMATTER: ModelStrategy.FAST,
    AgentRole.HUMANIZER: ModelStrategy.FAST,
    AgentRole.WORKER: ModelStrategy.FAST,
    AgentRole.CODER: ModelStrategy.FAST,
}


# ── Model Priority Patterns ─────────────────────────────
# Used by the router to sort discovered models into priority tiers.
# Each tuple is (pattern, anti_pattern, priority).
# Pattern matching is case-insensitive substring matching.
# Lower priority number = tried first.
MODEL_PRIORITY_PATTERNS: list[tuple[str, str | None, int]] = [
    ("manus", None, 5),  # Manus (top priority)
    ("gemini-2.5-flash", "lite", 10),  # Gemini 2.5 Flash (not lite)
    ("gemini-2.5-flash-lite", None, 20),  # Gemini 2.5 Flash Lite
    ("nemotron-3-ultra", None, 25),  # Nemotron 3 Ultra (fallback when Gemini exhausted)
    ("gemma-4", "26b", 30),  # Gemma 4 31B (not 26b)
    ("gemma-4", "31b", 40),  # Gemma 4 26B (not 31b)
    ("gemini-3.1-flash-lite", None, 45),  # Gemini 3.1 Flash Lite (fast, reliable)
    ("gemini-3.1-flash", "lite", 48),  # Gemini 3.1 Flash
    ("gemini-3", "lite", 50),  # Gemini 3 Flash
    ("gemini-3", None, 55),  # Gemini 3.x (lite variants)
    ("gemini-2.0-flash", None, 60),  # Gemini 2.0 Flash
    ("gemini-1.5-flash", None, 70),  # Gemini 1.5 Flash
    ("gemini-1.5-pro", None, 80),  # Gemini 1.5 Pro
]

# Models to EXCLUDE from routing pool (incompatible with system instructions, JSON mode, etc.)
EXCLUDED_MODEL_PATTERNS: list[str] = [
    "tts",  # Text-to-speech models don't support system instructions
    "image",  # Image generation models
    "audio",  # Audio models
    "embedding",  # Embedding-only models
    "vision",  # Vision-only models (if not multimodal)
    "realtime",  # Realtime models (different API)
]

# Default priority for any discovered model not matching patterns above
DEFAULT_MODEL_PRIORITY = 100


def get_model_config(role: AgentRole) -> ModelConfig:
    """Get the model configuration for a given agent role."""
    return MODEL_ROUTING[role]


def get_role_strategy(role: AgentRole) -> str:
    """Get the routing strategy for a given agent role."""
    return ROLE_STRATEGY_MAP.get(role, ModelStrategy.FAST).value


def compute_model_priority(model_id: str) -> int:
    """
    Compute priority for a model based on pattern matching.
    Lower number = higher priority = tried first.
    No hardcoded model names — pure pattern matching.
    """
    model_lower = model_id.lower()

    for pattern, anti_pattern, priority in MODEL_PRIORITY_PATTERNS:
        if pattern in model_lower:
            if anti_pattern and anti_pattern in model_lower:
                continue  # Skip if anti-pattern matches
            return priority

    return DEFAULT_MODEL_PRIORITY
