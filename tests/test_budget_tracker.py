"""Tests for src/utils/budget_tracker.py."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.utils.budget_tracker import (
    API_COSTS,
    MONTHLY_BUDGET,
    BudgetStatus,
    BudgetTracker,
)


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    """Create a BudgetTracker that reads/writes to tmp_path."""
    data_file = tmp_path / "budget_tracker.json"
    monkeypatch.setattr("src.utils.budget_tracker.DATA_FILE", data_file)
    return BudgetTracker()


# ── Basic tracking ──────────────────────────────────────────────


def test_track_returns_true_when_under_budget(tracker):
    assert tracker.track("alpaca_data") is True


def test_track_increments_spent(tracker):
    tracker.track("alpaca_data", cost=1.50)
    assert tracker.data["spent_this_month"] == pytest.approx(1.50)


def test_track_accumulates_multiple_calls(tracker):
    tracker.track("alpaca_data", cost=0.10)
    tracker.track("alpaca_data", cost=0.20)
    assert tracker.data["spent_this_month"] == pytest.approx(0.30)


def test_track_uses_default_cost_from_api_costs(tracker):
    tracker.track("openrouter_opus")
    assert tracker.data["spent_this_month"] == pytest.approx(API_COSTS["openrouter_opus"])


def test_track_unknown_api_defaults_to_0_001(tracker):
    tracker.track("unknown_api")
    assert tracker.data["spent_this_month"] == pytest.approx(0.001)


def test_track_records_api_call_count(tracker):
    tracker.track("alpaca_data")
    tracker.track("alpaca_data")
    tracker.track("yfinance")
    assert tracker.data["api_calls"]["alpaca_data"] == 2
    assert tracker.data["api_calls"]["yfinance"] == 1


def test_track_records_daily_spending(tracker):
    today = datetime.now().strftime("%Y-%m-%d")
    tracker.track("alpaca_data", cost=0.50)
    assert tracker.data["daily_spending"][today] == pytest.approx(0.50)


# ── Limit enforcement ──────────────────────────────────────────


def test_track_returns_false_when_budget_exceeded(tracker):
    # Spend the entire budget
    tracker.track("big_call", cost=MONTHLY_BUDGET)
    # Next call tips over
    result = tracker.track("one_more", cost=0.01)
    assert result is False


def test_track_returns_false_exactly_at_zero_remaining(tracker):
    """Spending exactly MONTHLY_BUDGET leaves remaining=0 -> False."""
    tracker.track("exact", cost=MONTHLY_BUDGET)
    # remaining is now 0; next call should be False
    result = tracker.track("next", cost=0.00)
    assert result is False


# ── Budget health ──────────────────────────────────────────────


def test_health_healthy_when_over_50_pct(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.40
    assert tracker._get_health() == "healthy"


def test_health_caution_between_20_and_50_pct(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.60
    assert tracker._get_health() == "caution"


def test_health_critical_under_20_pct(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.85
    assert tracker._get_health() == "critical"


def test_health_critical_when_overspent(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 1.10
    assert tracker._get_health() == "critical"


# ── should_execute (BATS-style) ────────────────────────────────


def test_critical_always_executes(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.99
    assert tracker.should_execute("trade", "critical") is True


def test_high_blocked_only_when_critical(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.85
    assert tracker.should_execute("analysis", "high") is False

    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.60
    assert tracker.should_execute("analysis", "high") is True


def test_medium_only_runs_when_healthy(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.10
    assert tracker.should_execute("research", "medium") is True

    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.60
    assert tracker.should_execute("research", "medium") is False


def test_low_only_runs_when_healthy(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.10
    assert tracker.should_execute("optional", "low") is True

    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.60
    assert tracker.should_execute("optional", "low") is False


# ── get_budget_status ──────────────────────────────────────────


def test_get_budget_status_returns_dataclass(tracker):
    status = tracker.get_budget_status()
    assert isinstance(status, BudgetStatus)
    assert status.monthly_budget == MONTHLY_BUDGET
    assert status.remaining == pytest.approx(MONTHLY_BUDGET)
    assert status.spent_this_month == pytest.approx(0.0)


def test_get_budget_status_reflects_spending(tracker):
    tracker.track("test_api", cost=25.0)
    status = tracker.get_budget_status()
    assert status.spent_this_month == pytest.approx(25.0)
    assert status.remaining == pytest.approx(MONTHLY_BUDGET - 25.0)


# ── Recommended model ─────────────────────────────────────────


def test_recommended_model_opus_when_healthy(tracker):
    tracker.data["spent_this_month"] = 0.0
    assert tracker.get_recommended_model() == "opus"


def test_recommended_model_sonnet_when_caution(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.60
    assert tracker.get_recommended_model() == "sonnet"


def test_recommended_model_haiku_when_critical(tracker):
    tracker.data["spent_this_month"] = MONTHLY_BUDGET * 0.85
    assert tracker.get_recommended_model() == "haiku"


# ── Prompt injection ───────────────────────────────────────────


def test_get_prompt_injection_contains_budget_info(tracker):
    prompt = tracker.get_prompt_injection()
    assert "BUDGET AWARENESS" in prompt
    assert f"${MONTHLY_BUDGET:.2f}" in prompt
    assert "HEALTHY" in prompt


# ── Persistence (file I/O) ─────────────────────────────────────


def test_data_persists_across_instances(tmp_path, monkeypatch):
    data_file = tmp_path / "budget_tracker.json"
    monkeypatch.setattr("src.utils.budget_tracker.DATA_FILE", data_file)

    t1 = BudgetTracker()
    t1.track("api_a", cost=10.0)

    t2 = BudgetTracker()
    assert t2.data["spent_this_month"] == pytest.approx(10.0)


def test_corrupted_file_reinitializes(tmp_path, monkeypatch):
    data_file = tmp_path / "budget_tracker.json"
    data_file.write_text("NOT JSON")
    monkeypatch.setattr("src.utils.budget_tracker.DATA_FILE", data_file)

    t = BudgetTracker()
    assert t.data["spent_this_month"] == 0.0


def test_new_month_resets_spending(tmp_path, monkeypatch):
    data_file = tmp_path / "budget_tracker.json"
    old_data = {
        "monthly_budget": MONTHLY_BUDGET,
        "spent_this_month": 80.0,
        "current_month": "1999-01",
        "api_calls": {},
        "daily_spending": {},
        "last_updated": "1999-01-31T00:00:00",
    }
    data_file.write_text(json.dumps(old_data))
    monkeypatch.setattr("src.utils.budget_tracker.DATA_FILE", data_file)

    t = BudgetTracker()
    assert t.data["spent_this_month"] == 0.0
    assert t.data["current_month"] == datetime.now().strftime("%Y-%m")


# ── Edge cases ─────────────────────────────────────────────────


def test_zero_cost_api_does_not_change_spent(tracker):
    tracker.track("yfinance")  # yfinance cost is 0.00
    assert tracker.data["spent_this_month"] == pytest.approx(0.0)


def test_explicit_zero_cost(tracker):
    tracker.track("anything", cost=0.0)
    assert tracker.data["spent_this_month"] == pytest.approx(0.0)


# ── Module-level convenience functions ─────────────────────────


def test_module_level_get_tracker_singleton(monkeypatch, tmp_path):
    """get_tracker() returns the same instance on repeated calls."""
    import src.utils.budget_tracker as mod

    data_file = tmp_path / "budget_tracker.json"
    monkeypatch.setattr(mod, "DATA_FILE", data_file)
    monkeypatch.setattr(mod, "_tracker", None)

    t1 = mod.get_tracker()
    t2 = mod.get_tracker()
    assert t1 is t2

    # cleanup global state
    monkeypatch.setattr(mod, "_tracker", None)
