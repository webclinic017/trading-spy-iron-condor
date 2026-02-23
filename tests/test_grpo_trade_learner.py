import json
import os
from pathlib import Path
import pytest
import numpy as np
from src.ml.grpo_trade_learner import GRPOTradeLearner, TradeFeatures, TradeParams

TEST_STATE_FILE = "data/test_grpo_state.json"


@pytest.fixture
def mock_learner():
    """Provides a learner instance with mock data."""
    learner = GRPOTradeLearner()

    # Generate 20 mock trades (minimum 16 for training)
    trades = []
    for i in range(20):
        is_win = i % 4 != 0  # 75% win rate
        trades.append(
            {
                "id": f"test-{i}",
                "symbol": "SPY260327P00650000",
                "side": "SELL" if is_win else "BUY",
                "qty": 1,
                "price": 1.5 if is_win else 4.0,
                "filled_at": f"2026-02-{10 + (i // 2):02d}T14:30:00Z",
            }
        )

    # Write to temporary file
    with open(TEST_STATE_FILE, "w") as f:
        json.dump({"trade_history": trades}, f)

    learner.load_trade_history(Path(TEST_STATE_FILE))
    yield learner

    # Cleanup
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)


def test_load_trade_history(mock_learner):
    """Verify that trade history processing works correctly."""
    # 20 raw trades grouped by date should yield ~10 processed cycles
    assert len(mock_learner.trade_history) >= 10
    assert mock_learner.trade_history[0].outcome in ["win", "loss"]


def test_calculate_rewards(mock_learner):
    """Ensure reward normalization centers around zero."""
    rewards = mock_learner.calculate_rewards()
    assert len(rewards) == len(mock_learner.trade_history)
    # Rewards should be normalized (mean ~0)
    assert abs(np.mean(rewards)) < 0.5


def test_predict_optimal_params(mock_learner):
    """Verify the policy outputs bounded parameters."""
    features = TradeFeatures(
        vix_level=20.0,
        vix_percentile=0.5,
        spy_20d_return=0.01,
        spy_5d_return=0.005,
        hour_of_day=0.5,
        day_of_week=0.5,
        days_to_expiry=30.0,
        put_call_ratio=1.0,
    )
    params = mock_learner.predict_optimal_params(features)

    assert 0.10 <= params.delta <= 0.25
    assert 21 <= params.dte <= 60
    assert 0.25 <= params.exit_profit_pct <= 0.75


def test_learning_summary(mock_learner):
    """Check if the summary correctly identifies winning/losing conditions."""
    summary = mock_learner.get_learning_summary()
    assert "win_rate" in summary
    assert "profit_factor" in summary
    assert summary["total_trades"] == len(mock_learner.trade_history)
