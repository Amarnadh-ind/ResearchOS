"""
Quota-Aware Model Routing Engine
Tracks per-model health, latency, cooldowns, and selects optimal models
based on strategy (fast vs quality) with automatic failover.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import structlog

from config.settings import get_settings

logger = structlog.get_logger()

# ── Quota error patterns ──────────────────────────────────
QUOTA_ERROR_PATTERNS = [
    "resource_exhausted",
    "rate_limit",
    "quota_exceeded",
    "too many requests",
    "rate limit exceeded",
    "quota has been exhausted",
    "requests per minute",
    "tokens per minute",
    "daily limit",
]

QUOTA_HTTP_CODES = {429, 503}


@dataclass
class ModelHealthRecord:
    """Tracks the health state of a single model."""

    model_id: str
    provider: str  # "gemini" or "gemma"
    priority: int = 999  # Lower = higher priority
    status: str = "online"  # online | cooldown | exhausted | unavailable
    requests_made: int = 0
    cooldown_until: datetime | None = None
    last_error: str = ""
    last_error_time: datetime | None = None
    last_success_time: datetime | None = None
    consecutive_failures: int = 0
    latency_history: deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def avg_latency_ms(self) -> float:
        """Rolling average latency from recent calls."""
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)

    @property
    def is_available(self) -> bool:
        """Check if model is available (not in cooldown or exhausted)."""
        if self.status == "unavailable":
            return False
        if self.status in ("cooldown", "exhausted"):
            if self.cooldown_until and datetime.utcnow() >= self.cooldown_until:
                # Cooldown expired — auto-recover
                self.status = "online"
                self.consecutive_failures = 0
                self.cooldown_until = None
                logger.info(
                    "model_cooldown_expired_auto_recovered",
                    model=self.model_id,
                )
                return True
            return False
        return True

    def to_telemetry(self) -> dict:
        """Return structured telemetry for diagnostics API."""
        cooldown_remaining = 0
        if self.cooldown_until:
            remaining = (self.cooldown_until - datetime.utcnow()).total_seconds()
            cooldown_remaining = max(0, int(remaining))

        return {
            "model": self.model_id,
            "provider": self.provider,
            "priority": self.priority,
            "status": self.status
            if self.is_available or self.status != "cooldown"
            else self.status,
            "latency_ms": int(self.avg_latency_ms),
            "requests_used": self.requests_made,
            "cooldown_remaining_s": cooldown_remaining,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None,
        }


class QuotaTracker:
    """
    Manages health records for all models and provides quota-aware routing.

    Responsibilities:
    - Track per-model health, latency, and request counts
    - Detect quota errors and trigger automatic cooldowns
    - Auto-recover models after cooldown expiry
    - Select optimal model based on strategy (fast/quality)
    - Provide real-time telemetry for diagnostics
    """

    def __init__(self):
        self._models: dict[str, ModelHealthRecord] = {}
        self._cooldown_seconds: int = get_settings().model_cooldown_seconds

    def register_model(self, model_id: str, provider: str, priority: int) -> None:
        """Register a model in the tracker."""
        if model_id not in self._models:
            self._models[model_id] = ModelHealthRecord(
                model_id=model_id,
                provider=provider,
                priority=priority,
            )
            logger.info(
                "quota_tracker_model_registered",
                model=model_id,
                provider=provider,
                priority=priority,
            )
        else:
            # Update priority if already registered
            self._models[model_id].priority = priority

    def unregister_all(self) -> None:
        """Clear all tracked models (used during re-discovery)."""
        self._models.clear()

    def mark_success(self, model_id: str, latency_ms: int) -> None:
        """Record a successful API call."""
        record = self._models.get(model_id)
        if not record:
            return

        record.status = "online"
        record.requests_made += 1
        record.consecutive_failures = 0
        record.last_success_time = datetime.utcnow()
        record.latency_history.append(latency_ms)
        record.last_error = ""
        record.cooldown_until = None

        logger.info(
            "quota_tracker_success",
            model=model_id,
            latency_ms=latency_ms,
            requests_made=record.requests_made,
            avg_latency=int(record.avg_latency_ms),
        )

    def mark_failure(self, model_id: str, error_msg: str, status_code: int = 0) -> None:
        """
        Record a failed API call. If it's a quota error, trigger cooldown.
        Uses adaptive cooldown based on error type.
        """
        record = self._models.get(model_id)
        if not record:
            return

        record.consecutive_failures += 1
        record.last_error = error_msg[:500]
        record.last_error_time = datetime.utcnow()

        is_quota_error = self._is_quota_error(error_msg, status_code)

        if is_quota_error:
            # Quota exhaustion — put model on cooldown (longer cooldown)
            record.status = "cooldown"
            record.cooldown_until = datetime.utcnow() + timedelta(seconds=self._cooldown_seconds)
            logger.warning(
                "quota_tracker_model_cooldown",
                model=model_id,
                reason=error_msg[:200],
                status_code=status_code,
                cooldown_seconds=self._cooldown_seconds,
                cooldown_until=record.cooldown_until.isoformat(),
            )
        elif status_code in (400, 403, 404):
            # Auth or model not found — mark unavailable (won't auto-recover)
            record.status = "unavailable"
            logger.error(
                "quota_tracker_model_unavailable",
                model=model_id,
                reason=error_msg[:200],
                status_code=status_code,
            )
        elif status_code == 503:
            # Service unavailable / overloaded — medium cooldown, will retry
            record.status = "cooldown"
            medium_cooldown = min(self._cooldown_seconds, 180)  # 3 min max for 503
            record.cooldown_until = datetime.utcnow() + timedelta(seconds=medium_cooldown)
            logger.warning(
                "quota_tracker_model_overloaded",
                model=model_id,
                reason=error_msg[:200],
                cooldown_seconds=medium_cooldown,
            )
        elif record.consecutive_failures >= 3:
            # Repeated non-quota failures — short cooldown
            record.status = "cooldown"
            short_cooldown = min(self._cooldown_seconds, 60)  # 1 min max for other errors
            record.cooldown_until = datetime.utcnow() + timedelta(seconds=short_cooldown)
            logger.warning(
                "quota_tracker_model_short_cooldown",
                model=model_id,
                consecutive_failures=record.consecutive_failures,
                cooldown_seconds=short_cooldown,
            )
        else:
            logger.warning(
                "quota_tracker_model_failure",
                model=model_id,
                error=error_msg[:200],
                status_code=status_code,
                consecutive_failures=record.consecutive_failures,
            )

    def is_available(self, model_id: str) -> bool:
        """Check if a model is available for requests."""
        record = self._models.get(model_id)
        if not record:
            return False
        return record.is_available

    def get_best_model(self, strategy: str, candidates: list[str]) -> str | None:
        """
        Select the best available model based on strategy.

        Strategies:
        - "fast": lowest avg_latency_ms among available models
        - "quality": highest priority (lowest priority number) among available
        """
        available = []
        for model_id in candidates:
            record = self._models.get(model_id)
            if record and record.is_available:
                available.append(record)

        if not available:
            return None

        if strategy == "fast":
            # Prefer models with latency data, sorted by latency
            with_latency = [r for r in available if r.latency_history]
            without_latency = [r for r in available if not r.latency_history]

            if with_latency:
                best = min(with_latency, key=lambda r: r.avg_latency_ms)
                return best.model_id
            elif without_latency:
                # No latency data yet — use priority order
                best = min(without_latency, key=lambda r: r.priority)
                return best.model_id
        elif strategy == "quality":
            # Use priority order (lower number = higher quality)
            best = min(available, key=lambda r: r.priority)
            return best.model_id

        # Default: priority order
        best = min(available, key=lambda r: r.priority)
        return best.model_id

    def get_ordered_candidates(self, strategy: str, all_candidates: list[str]) -> list[str]:
        """
        Return an ordered list of available model IDs based on strategy.
        Unavailable models are excluded. Used for failover chain.
        """
        available = []
        skipped = []

        for model_id in all_candidates:
            record = self._models.get(model_id)
            if record and record.is_available:
                available.append(record)
            else:
                skipped.append(model_id)

        if skipped:
            logger.info(
                "quota_tracker_skipped_models",
                skipped=skipped,
                reason="cooldown or unavailable",
            )

        if strategy == "fast":
            with_latency = [r for r in available if r.latency_history]
            without_latency = [r for r in available if not r.latency_history]
            # Sort those with data by latency, then append untested by priority
            with_latency.sort(key=lambda r: r.avg_latency_ms)
            without_latency.sort(key=lambda r: r.priority)
            ordered = with_latency + without_latency
        else:
            # Quality: strict priority order
            ordered = sorted(available, key=lambda r: r.priority)

        return [r.model_id for r in ordered]

    def get_telemetry(self) -> dict:
        """Return full telemetry for all tracked models."""
        models = {}
        for model_id, record in self._models.items():
            # Force availability check to auto-recover expired cooldowns
            _ = record.is_available
            models[model_id] = record.to_telemetry()

        # Summary stats
        online_count = sum(1 for r in self._models.values() if r.status == "online")
        cooldown_count = sum(1 for r in self._models.values() if r.status == "cooldown")
        unavailable_count = sum(1 for r in self._models.values() if r.status == "unavailable")

        return {
            "models": models,
            "summary": {
                "total": len(self._models),
                "online": online_count,
                "cooldown": cooldown_count,
                "unavailable": unavailable_count,
            },
        }

    def get_model_record(self, model_id: str) -> ModelHealthRecord | None:
        """Get the health record for a specific model."""
        return self._models.get(model_id)

    @staticmethod
    def _is_quota_error(error_msg: str, status_code: int) -> bool:
        """Detect whether an error is a quota/rate-limit error."""
        if status_code in QUOTA_HTTP_CODES:
            return True

        error_lower = error_msg.lower()
        return any(pattern in error_lower for pattern in QUOTA_ERROR_PATTERNS)

    @staticmethod
    def classify_error(error_msg: str, status_code: int) -> str:
        """Classify error into actionable categories for dashboard and routing."""
        error_lower = error_msg.lower()

        if status_code == 429 or any(
            p in error_lower
            for p in [
                "resource_exhausted",
                "rate_limit",
                "quota_exceeded",
                "too many requests",
                "rate limit exceeded",
                "quota has been exhausted",
                "requests per minute",
                "tokens per minute",
                "daily limit",
            ]
        ):
            return "quota_exceeded"

        if status_code in (400, 403, 404):
            if any(
                p in error_lower
                for p in ["invalid api key", "unauthorized", "forbidden", "invalid key"]
            ):
                return "invalid_key"
            if any(
                p in error_lower
                for p in [
                    "not found",
                    "not enabled",
                    "not supported",
                    "invalid argument",
                    "developer instruction",
                    "system instruction",
                    "response_mime_type",
                    "json mode",
                ]
            ):
                return "permanent_failure"
            return "unavailable_model"

        if status_code == 503:
            return "service_overloaded"

        if status_code == 0 and any(
            p in error_lower for p in ["connect", "timeout", "dns", "network", "connection"]
        ):
            return "network_error"

        return "unknown"

    @staticmethod
    def get_recovery_info(record, cooldown_remaining: int) -> dict:
        """Generate recovery information for a model."""
        if not record:
            return {"action": "unknown", "eta_seconds": 0, "auto_recovers": False}

        if record.status == "online":
            return {"action": "healthy", "eta_seconds": 0, "auto_recovers": True}

        if record.status == "unavailable":
            return {
                "action": "manual_intervention_required",
                "eta_seconds": 0,
                "auto_recovers": False,
                "reason": "Model marked unavailable (auth failure or incompatible). Check API keys or model compatibility.",
            }

        if record.status == "cooldown":
            if cooldown_remaining > 0:
                return {
                    "action": "waiting_cooldown",
                    "eta_seconds": cooldown_remaining,
                    "auto_recovers": True,
                    "reason": f"Cooldown expires in {cooldown_remaining}s",
                }
            else:
                return {
                    "action": "cooldown_expired_recovering",
                    "eta_seconds": 0,
                    "auto_recovers": True,
                    "reason": "Cooldown expired, will recover on next check",
                }

        return {"action": "unknown", "eta_seconds": 0, "auto_recovers": False}


# ── Singleton ──────────────────────────────────────────────
_quota_tracker: QuotaTracker | None = None


def get_quota_tracker() -> QuotaTracker:
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = QuotaTracker()
    return _quota_tracker


def reset_quota_tracker() -> None:
    """Reset the global tracker (used in tests)."""
    global _quota_tracker
    _quota_tracker = None
