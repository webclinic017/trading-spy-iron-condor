import json
import os
from pathlib import Path
import pytest
from src.orchestration.harness.rlm_orchestrator import RLMOrchestrator, RLMTask


@pytest.fixture
def mock_trades_env():
    """Create mock trade data for RLM testing."""
    test_dir = Path("data/test_rlm")
    os.makedirs(test_dir, exist_ok=True)

    trade_file = test_dir / "trades_test.json"
    mock_trades = [
        {"symbol": "SPY", "pnl": 100.0, "status": "closed"},
        {"symbol": "QQQ", "pnl": -50.0, "status": "closed"},
        {"symbol": "SPY", "pnl": 200.0, "status": "closed"},
    ]

    with open(trade_file, "w") as f:
        json.dump(mock_trades, f)

    yield str(trade_file)

    # Cleanup
    if trade_file.exists():
        os.remove(trade_file)
    if test_dir.exists():
        os.rmdir(test_dir)


def test_rlm_algorithm_1_trade_aggregation(mock_trades_env):
    """Verify that RLM correctly aggregates trades with Zero Sub-calls."""
    orchestrator = RLMOrchestrator()

    task = RLMTask(
        id="test_task",
        task_type="trade_aggregation",
        query="Analyze mock trades",
        data_paths=[mock_trades_env],
    )

    result = orchestrator.execute_algorithm_1(task)

    assert result["total_trades"] == 3
    assert result["net_pnl"] == 250.0
    # SPY won twice, QQQ lost once. Top winner should be SPY.
    assert result["top_winning_tickers"][0][0] == "SPY"
    assert result["top_winning_tickers"][0][1] == 2
    assert "RLM Algorithm 1" in result["methodology"]


def test_rlm_invalid_task_type():
    """Verify that RLM handles unknown task types gracefully."""
    orchestrator = RLMOrchestrator()
    task = RLMTask(id="fail", task_type="invalid", query="N/A", data_paths=[])

    result = orchestrator.execute_algorithm_1(task)
    assert result["status"] == "error"
