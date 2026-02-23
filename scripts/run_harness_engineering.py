import logging

import yaml
from src.orchestration.harness.strategy_harness import StrategyHarness, StrategyIdea

# Harness Engineering Orchestrator
# This script powers the 'Zero-Manual-Code' methodology from OpenAI's Harness Engineering.

logger = logging.getLogger(__name__)


def run_harness_loop(idea_file="config/strategy_ideas.yaml"):
    """
    Automates the entire strategy development lifecycle:
    Declarative Idea -> Prompt -> Code Gen -> Deploy -> Test -> Verify.
    """
    # 1. Load the Declarative Idea
    with open(idea_file) as f:
        config = yaml.safe_load(f)
        strat_config = config["strategy"]

    idea = StrategyIdea(
        name=strat_config["name"],
        description=strat_config["description"],
        universe=strat_config["universe"],
        signals=strat_config["signals"],
        risk_params=strat_config["risk_params"],
        target_filename=strat_config["target_filename"],
    )

    harness = StrategyHarness()

    # 2. Generate the Harness Engineering Prompt
    prompt = harness.generate_strategy_code_prompt(idea)
    print("\n--- [ HARNESS PROMPT START ] ---")
    print(prompt)
    print("--- [ HARNESS PROMPT END ] ---\n")

    # 3. Instruction for the user to use the prompt with Local LLM (Claude Code)
    print("🚀 PRO-TIP: Run the following command with Claude Code to generate the strategy:")
    print(f"claude code '{prompt}'")

    # 4. In a fully autonomous loop, we would capture the output here.
    # For now, we prepare the infrastructure for the 'Harness Deployment'.
    # Example deployment (simulated):
    # harness.deploy_harness_output(idea, "(Generated code from Claude Code would go here)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_harness_loop()
