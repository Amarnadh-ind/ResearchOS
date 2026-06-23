"""
Tests for Model Cooldown Mechanics
Verifies cooldown timers, auto-recovery, independent cooldowns, and configurability.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.quota_tracker import QuotaTracker, reset_quota_tracker


@pytest.fixture(autouse=True)
def clean_tracker():
    """Reset quota tracker before each test."""
    reset_quota_tracker()
    yield


def build_tracker(cooldown_seconds: int = 600) -> QuotaTracker:
    """Create a tracker with test models."""
    tracker = QuotaTracker.__new__(QuotaTracker)
    tracker._models = {}
    tracker._cooldown_seconds = cooldown_seconds

    tracker.register_model("gemini-2.5-flash", "gemini", 10)
    tracker.register_model("gemini-2.5-flash-lite", "gemini", 20)
    tracker.register_model("gemma-4-31b-it", "gemma", 30)

    return tracker


def test_cooldown_marks_model_unavailable():
    """After a 429, model is marked as unavailable during cooldown period."""
    tracker = build_tracker()

    # Simulate a quota error
    tracker.mark_failure("gemini-2.5-flash", "Rate limit exceeded", 429)

    # Model should be in cooldown
    record = tracker.get_model_record("gemini-2.5-flash")
    assert record.status == "cooldown"
    assert not tracker.is_available("gemini-2.5-flash")
    assert record.cooldown_until is not None
    assert record.cooldown_until > datetime.utcnow()


def test_cooldown_auto_recovery():
    """After cooldown expires, model becomes available again."""
    tracker = build_tracker(cooldown_seconds=1)

    # Trigger cooldown
    tracker.mark_failure("gemini-2.5-flash", "Rate limit", 429)
    assert not tracker.is_available("gemini-2.5-flash")

    # Manually set cooldown to already-expired
    record = tracker.get_model_record("gemini-2.5-flash")
    record.cooldown_until = datetime.utcnow() - timedelta(seconds=1)

    # Now model should be available (auto-recovered on check)
    assert tracker.is_available("gemini-2.5-flash")
    assert record.status == "online"
    assert record.consecutive_failures == 0


def test_multiple_models_independent_cooldowns():
    """Each model has its own independent cooldown timer."""
    tracker = build_tracker()

    # Model A gets quota error
    tracker.mark_failure("gemini-2.5-flash", "Rate limit", 429)

    # Model B is still available
    assert not tracker.is_available("gemini-2.5-flash")
    assert tracker.is_available("gemini-2.5-flash-lite")
    assert tracker.is_available("gemma-4-31b-it")


def test_cooldown_duration_configurable():
    """Cooldown duration respects the configured seconds."""
    # Short cooldown
    tracker_short = build_tracker(cooldown_seconds=30)
    tracker_short.mark_failure("gemini-2.5-flash", "Rate limit", 429)
    record_short = tracker_short.get_model_record("gemini-2.5-flash")
    expected_short = datetime.utcnow() + timedelta(seconds=30)
    assert abs((record_short.cooldown_until - expected_short).total_seconds()) < 2

    # Long cooldown
    tracker_long = build_tracker(cooldown_seconds=1800)
    tracker_long.mark_failure("gemini-2.5-flash", "Rate limit", 429)
    record_long = tracker_long.get_model_record("gemini-2.5-flash")
    expected_long = datetime.utcnow() + timedelta(seconds=1800)
    assert abs((record_long.cooldown_until - expected_long).total_seconds()) < 2


def test_non_quota_errors_dont_trigger_immediate_cooldown():
    """Non-quota errors (like 500) don't trigger immediate cooldown,
    but 3 consecutive failures do trigger a short cooldown."""
    tracker = build_tracker()

    # First failure — not cooldown
    tracker.mark_failure("gemini-2.5-flash", "Internal server error", 500)
    assert tracker.is_available("gemini-2.5-flash")

    # Second failure — still not cooldown
    tracker.mark_failure("gemini-2.5-flash", "Internal server error", 500)
    assert tracker.is_available("gemini-2.5-flash")

    # Third failure — triggers short cooldown
    tracker.mark_failure("gemini-2.5-flash", "Internal server error", 500)
    assert not tracker.is_available("gemini-2.5-flash")
    record = tracker.get_model_record("gemini-2.5-flash")
    assert record.status == "cooldown"


def test_success_resets_consecutive_failures():
    """A successful call resets the consecutive failure counter."""
    tracker = build_tracker()

    tracker.mark_failure("gemini-2.5-flash", "Error 1", 500)
    tracker.mark_failure("gemini-2.5-flash", "Error 2", 500)
    record = tracker.get_model_record("gemini-2.5-flash")
    assert record.consecutive_failures == 2

    # Success resets
    tracker.mark_success("gemini-2.5-flash", 100)
    assert record.consecutive_failures == 0
    assert record.status == "online"


def test_auth_errors_mark_unavailable():
    """403/400 errors mark model as unavailable (won't auto-recover)."""
    tracker = build_tracker()

    tracker.mark_failure("gemini-2.5-flash", "Invalid API key", 403)
    assert not tracker.is_available("gemini-2.5-flash")

    record = tracker.get_model_record("gemini-2.5-flash")
    assert record.status == "unavailable"

    # Even after "cooldown" time, it remains unavailable
    record.cooldown_until = datetime.utcnow() - timedelta(hours=1)
    assert not tracker.is_available("gemini-2.5-flash")


def test_telemetry_includes_cooldown_remaining():
    """Telemetry output includes cooldown remaining seconds."""
    tracker = build_tracker()
    tracker.mark_failure("gemini-2.5-flash", "Rate limit", 429)

    telemetry = tracker.get_telemetry()
    model_info = telemetry["models"]["gemini-2.5-flash"]
    assert model_info["status"] == "cooldown"
    assert model_info["cooldown_remaining_s"] > 0
    assert model_info["last_error"] == "Rate limit"
