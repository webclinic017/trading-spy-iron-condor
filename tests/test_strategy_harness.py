from pathlib import Path

import pytest

from src.orchestration.harness.strategy_harness import StrategyHarness, StrategyIdea


@pytest.fixture
def test_harness_env(tmp_path: Path):
    """Create a temporary test environment for the Harness."""
    test_dir = tmp_path / "tmp_harness_env"
    strategies_dir = test_dir / "src/strategies"
    tests_dir = test_dir / "tests"
    (test_dir / "config").mkdir(parents=True)
    strategies_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    # Initialize Harness with test root
    harness = StrategyHarness(root_dir=str(test_dir))

    yield harness


def test_generate_strategy_prompt(test_harness_env):
    """Verify the Harness generates a correct prompt."""
    idea = StrategyIdea(
        name="TestStrategy",
        description="A test strategy",
        universe=["AAPL"],
        signals=["RSI < 20"],
        risk_params={"stop_loss": 0.01},
        target_filename="test_strategy.py",
    )

    prompt = test_harness_env.generate_strategy_code_prompt(idea)

    assert "NAME: TestStrategy" in prompt
    assert "UNIVERSE: ['AAPL']" in prompt
    assert "Inherit from 'BaseStrategy'" in prompt


def test_deploy_harness_output(test_harness_env):
    """Verify that code deployment works correctly."""
    idea = StrategyIdea(
        name="MockStrategy",
        description="Mock description",
        universe=["SPY"],
        signals=["Mock Signal"],
        risk_params={},
        target_filename="mock_strategy.py",
    )

    mock_code = "class MockStrategy: pass"

    # Execute Deployment
    test_harness_env.deploy_harness_output(idea, mock_code)

    # Check Strategy File
    strategy_file = test_harness_env.strategies_dir / "mock_strategy.py"
    assert strategy_file.exists()
    assert strategy_file.read_text() == mock_code

    # Check Test File Generation
    test_file = test_harness_env.tests_dir / "test_mock_strategy.py"
    assert test_file.exists()
    assert "test_mockstrategy_initialization" in test_file.read_text()
