# Harness Engineering Codex

This document outlines the **Harness Engineering** methodology used in our trading system, inspired by OpenAI's internal practices.

## 🧠 Philosophy
We do not write trading strategies by hand. We design **Harnesses**—declarative environments where AI agents implement logic based on structured constraints.

## 🛠️ The Harness Workflow

1.  **Define the Idea**:
    Edit `config/strategy_ideas.yaml`. Describe the strategy's *intent* (not implementation).
    ```yaml
    strategy:
      name: "GapAndGo"
      description: "Buy gapping stocks at open."
      signals: ["Open > PrevClose * 1.02"]
    ```

2.  **Generate the Prompt**:
    Run the orchestrator to convert your idea into a high-precision engineering prompt.
    ```bash
    python3 scripts/run_harness_engineering.py
    ```

3.  **Execute with Local LLM**:
    Copy the output command and run it with Claude Code (connected to Unsloth).
    ```bash
    claude code '<generated_prompt>'
    ```

4.  **Verify & Deploy**:
    The Harness automatically:
    - Writes the `.py` file to `src/strategies/`.
    - Generates a `test_*.py` file in `tests/`.
    - Runs `ruff` linting and `pytest` verification.

## 📊 ROI & Metrics
- **Zero Tech Debt**: All generated code must pass the `BaseStrategy` interface and strict linting.
- **Speed**: Move from "Idea" to "Backtestable Code" in < 2 minutes.
- **Security**: Logic is generated locally; no IP leakage to cloud APIs.

---
*Reference: [OpenAI Harness Engineering](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/)*
