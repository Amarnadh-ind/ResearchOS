"""
Base Agent Protocol
Defines the contract all agents must implement.
"""

import time
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base for all ResearchOS agents."""

    name: str = "base_agent"

    @abstractmethod
    async def execute(self, input_data: dict, context: dict) -> dict:
        """Execute the agent's task. Must be implemented by subclasses."""
        ...

    async def run(self, input_data: dict, context: dict) -> dict:
        """Run the agent with logging, timing, and error handling."""
        start = time.monotonic()
        logger.info("agent_start", agent=self.name)

        try:
            result = await self.execute(input_data, context)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "agent_complete",
                agent=self.name,
                duration_ms=duration_ms,
            )
            return {
                "status": "success",
                "agent": self.name,
                "data": result,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "agent_error",
                agent=self.name,
                error=str(e),
                duration_ms=duration_ms,
            )
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "duration_ms": duration_ms,
            }

    def verify_output(self, output: dict) -> bool:
        """Verification gate — override in subclasses for custom validation."""
        return output.get("status") == "success"
