"""Tests for API Circuit Breaker."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.utils.api_circuit_breaker import (
    APICircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
    MAX_CONSECUTIVE_FAILURES,
    COOLDOWN_SECONDS,
    check_circuit_breaker,
)


@pytest.fixture(autouse=True)
def fresh_breaker():
    """Reset singleton state before each test so tests are isolated."""
    APICircuitBreaker._instance = None
    APICircuitBreaker._lock.__class__()  # not strictly needed but documents intent
    with patch.object(APICircuitBreaker, "_load_state"), \
         patch.object(APICircuitBreaker, "_save_state"), \
         patch.object(APICircuitBreaker, "_send_alert"):
        breaker = APICircuitBreaker()
        yield breaker
    # Clean up singleton so next test starts fresh
    APICircuitBreaker._instance = None


# ── Closed state (normal operation) ─────────────────────────────────────


def test_initial_state_is_closed(fresh_breaker):
    assert fresh_breaker.is_open() is False
    assert fresh_breaker.consecutive_failures == 0
    assert fresh_breaker.trip_count == 0


def test_record_success_keeps_closed(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"):
        fresh_breaker.record_success()
    assert fresh_breaker.is_open() is False
    assert fresh_breaker.consecutive_failures == 0
    assert fresh_breaker.last_success_time is not None


def test_failures_below_threshold_stay_closed(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES - 1):
            fresh_breaker.record_failure(f"error {i}")
    assert fresh_breaker.is_open() is False
    assert fresh_breaker.consecutive_failures == MAX_CONSECUTIVE_FAILURES - 1


# ── Tripping (closed -> open) ───────────────────────────────────────────


def test_trips_at_threshold(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert") as mock_alert:
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
    assert fresh_breaker.is_open() is True
    assert fresh_breaker.trip_count == 1
    assert fresh_breaker.trip_time is not None
    mock_alert.assert_called_once()


def test_trips_exactly_at_threshold_not_before(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES - 1):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker._is_open is False

        fresh_breaker.record_failure("final error")
        assert fresh_breaker._is_open is True


def test_extra_failures_after_trip_do_not_increment_trip_count(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES + 3):
            fresh_breaker.record_failure(f"error {i}")
    # _trip() returns early if already open, so trip_count stays 1
    assert fresh_breaker.trip_count == 1


# ── Open state ──────────────────────────────────────────────────────────


def test_is_open_returns_true_during_cooldown(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
    assert fresh_breaker.is_open() is True


def test_check_circuit_breaker_raises_when_open(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")

    with patch("src.utils.api_circuit_breaker.get_api_circuit_breaker", return_value=fresh_breaker):
        with pytest.raises(CircuitBreakerOpen):
            check_circuit_breaker()


def test_check_circuit_breaker_ok_when_closed(fresh_breaker):
    with patch("src.utils.api_circuit_breaker.get_api_circuit_breaker", return_value=fresh_breaker):
        check_circuit_breaker()  # should not raise


# ── Cooldown expiry (open -> half-open/closed) ──────────────────────────


def test_cooldown_expiry_resets_breaker(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")

    assert fresh_breaker.is_open() is True

    # Simulate time passing beyond cooldown
    fresh_breaker.trip_time = datetime.now() - timedelta(seconds=COOLDOWN_SECONDS + 1)
    with patch.object(fresh_breaker, "_save_state"):
        assert fresh_breaker.is_open() is False
    assert fresh_breaker.consecutive_failures == 0
    assert fresh_breaker._is_open is False


def test_cooldown_not_expired_stays_open(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")

    # trip_time is "now", so cooldown has not expired
    assert fresh_breaker.is_open() is True


# ── Recovery (success after failures) ───────────────────────────────────


def test_success_resets_failure_counter(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(3):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker.consecutive_failures == 3

        fresh_breaker.record_success()
    assert fresh_breaker.consecutive_failures == 0
    assert fresh_breaker.is_open() is False


def test_success_clears_open_state(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker._is_open is True

        fresh_breaker.record_success()
    assert fresh_breaker._is_open is False
    assert fresh_breaker.consecutive_failures == 0


def test_success_after_cooldown_expiry(fresh_breaker):
    """After cooldown expires and a success comes in, state is fully reset."""
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")

    fresh_breaker.trip_time = datetime.now() - timedelta(seconds=COOLDOWN_SECONDS + 1)
    with patch.object(fresh_breaker, "_save_state"):
        # is_open() triggers _reset via cooldown expiry
        assert fresh_breaker.is_open() is False
        fresh_breaker.record_success()
    assert fresh_breaker.consecutive_failures == 0
    assert fresh_breaker.last_success_time is not None


# ── get_status ──────────────────────────────────────────────────────────


def test_get_status_returns_dataclass(fresh_breaker):
    status = fresh_breaker.get_status()
    assert isinstance(status, CircuitBreakerState)
    assert status.is_open is False
    assert status.consecutive_failures == 0
    assert status.trip_count == 0
    assert status.last_failure_time is None
    assert status.last_success_time is None
    assert status.trip_time is None


def test_get_status_reflects_failures(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")

    status = fresh_breaker.get_status()
    assert status.is_open is True
    assert status.consecutive_failures == MAX_CONSECUTIVE_FAILURES
    assert status.trip_count == 1
    assert status.trip_time is not None
    assert status.last_failure_time is not None


# ── Edge cases ──────────────────────────────────────────────────────────


def test_trip_with_no_trip_time_stays_open(fresh_breaker):
    """If trip_time is None but _is_open is True, is_open() returns True."""
    fresh_breaker._is_open = True
    fresh_breaker.trip_time = None
    assert fresh_breaker.is_open() is True


def test_interleaved_failures_and_successes(fresh_breaker):
    """Successes reset the counter so it takes another full run to trip."""
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        for i in range(MAX_CONSECUTIVE_FAILURES - 1):
            fresh_breaker.record_failure(f"error {i}")
        fresh_breaker.record_success()  # reset
        assert fresh_breaker.consecutive_failures == 0

        # Need full threshold again to trip
        for i in range(MAX_CONSECUTIVE_FAILURES - 1):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker._is_open is False


def test_multiple_trips_across_resets(fresh_breaker):
    """Trip count accumulates across resets."""
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert"):
        # First trip
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker.trip_count == 1

        # Recovery
        fresh_breaker.record_success()
        assert fresh_breaker._is_open is False

        # Second trip
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
        assert fresh_breaker.trip_count == 2


def test_send_alert_called_on_trip(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert") as mock_alert:
        for i in range(MAX_CONSECUTIVE_FAILURES):
            fresh_breaker.record_failure(f"error {i}")
    mock_alert.assert_called_once_with(f"error {MAX_CONSECUTIVE_FAILURES - 1}")


def test_send_alert_not_called_below_threshold(fresh_breaker):
    with patch.object(fresh_breaker, "_save_state"), \
         patch.object(fresh_breaker, "_send_alert") as mock_alert:
        for i in range(MAX_CONSECUTIVE_FAILURES - 1):
            fresh_breaker.record_failure(f"error {i}")
    mock_alert.assert_not_called()


def test_circuit_breaker_open_exception_is_exception():
    assert issubclass(CircuitBreakerOpen, Exception)
    exc = CircuitBreakerOpen("halted")
    assert str(exc) == "halted"
