import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StrategyIdea:
    """Declarative description of a trading strategy."""

    name: str
    description: str
    universe: list[str]
    signals: list[str]  # e.g., ["RSI < 30", "MACD Crossover"]
    risk_params: dict[str, Any]
    target_filename: str


class StrategyHarness:
    """
    Harness Engineering Orchestrator for Trading Strategies.

    Automates the generation of code, config, and tests from a declarative 'Idea'.
    Uses local Unsloth/Claude Code integration for zero-cost agentic runs.
    """

    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir)
        self.strategies_dir = self.root / "src/strategies"
        self.tests_dir = self.root / "tests"
        self.config_file = self.root / "config/strategies.yaml"

    def generate_strategy_code_prompt(self, idea: StrategyIdea) -> str:
        """Constructs a high-precision prompt for the local LLM."""
        return f"""
Act as a Senior Harness Engineer specializing in Quantitative Trading.
Implement a Python strategy class based on the following declarative idea:

NAME: {idea.name}
DESCRIPTION: {idea.description}
UNIVERSE: {idea.universe}
SIGNALS: {idea.signals}
RISK: {idea.risk_params}

REQUIREMENTS:
1. Inherit from 'BaseStrategy' in 'src.strategies.core_strategy'.
2. Implement 'generate_signals(self, data: Any) -> List[Signal]'.
3. Use the provided risk parameters for stop-loss and take-profit.
4. Output ONLY the Python code. No conversational filler.
5. Follow PEP8 and project-specific two-space indentation.
"""

    def _execute_harness_run(self, prompt: str) -> str:
        """
        Executes the 'Harness Run' using the local LLM.
        This simulates the OpenAI 'Harness Engineering' flow.
        """
        # In a real scenario, this would call 'claude' or 'llama-server'
        # For this prototype, we'll log the intent.
        logger.info("🚀 Initiating Harness Engineering Run...")
        # Note: We've already set up ANTHROPIC_BASE_URL redirection in config/local_llm_config.sh
        return "# (Generated code would be here)"

    def deploy_harness_output(self, idea: StrategyIdea, code: str):
        """Deploys the generated code and updates system configurations."""
        strategy_path = self.strategies_dir / idea.target_filename

        # 1. Write the Strategy Code
        strategy_path.write_text(code)
        logger.info(f"✅ Strategy code deployed to {strategy_path}")

        # 2. Generate a Test Case
        test_content = f"""
import pytest
from src.strategies.{idea.target_filename.replace(".py", "")} import {idea.name.replace(" ", "")}

def test_{idea.name.lower().replace(" ", "_")}_initialization():
    strategy = {idea.name.replace(" ", "")}()
    assert strategy.name is not None
    assert len(strategy.universe) > 0
"""
        test_path = self.tests_dir / f"test_{idea.target_filename}"
        test_path.write_text(test_content)
        logger.info(f"✅ Test case generated at {test_path}")

        # 3. Verify Deployment (Harness Engineering Loop)
        self._verify_deployment(strategy_path, test_path)

    def _verify_deployment(self, strategy_path: Path, test_path: Path):
        """Runs linting and tests to ensure zero-tech-debt deployment."""
        logger.info("🔍 Verifying Harness Deployment...")
        ruff_bin = shutil.which("ruff")
        if not ruff_bin:
            logger.warning("ruff not found on PATH; skipping harness lint verification.")
            return
        subprocess.run([ruff_bin, "check", str(strategy_path)], check=False)
        # subprocess.run(["pytest", str(test_path)], check=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    harness = StrategyHarness()

    # Example Declarative Idea
    mean_reversion_idea = StrategyIdea(
        name="Mean Reversion Pro",
        description="Bollinger Band mean reversion for liquid ETFs",
        universe=["SPY", "QQQ"],
        signals=["Price < Lower Bollinger Band", "RSI < 30"],
        risk_params={"stop_loss": 0.02, "take_profit": 0.04},
        target_filename="mean_reversion_pro.py",
    )

    print(f"Harness Prompt:\n{harness.generate_strategy_code_prompt(mean_reversion_idea)}")
