# Update Diagrams - Regenerate All Architecture Diagrams

Regenerate all PaperBanana architecture diagrams from their source descriptions.

## Usage

```
/update-diagrams [--force]
```

## Arguments

- `--force` (optional): Regenerate even if diagrams already exist

## What It Does

1. Reads all `.txt` description files from `docs/assets/diagram_*.txt`
2. For each description, runs PaperBanana to generate/update the corresponding PNG
3. Updates the README if any diagrams changed
4. Commits the updated diagrams

## Source Files

| Description | Output | Caption |
|---|---|---|
| `docs/assets/diagram_llm_gateway.txt` | `docs/assets/llm_gateway_architecture.png` | Multi-Model LLM Gateway with TARS |
| `docs/assets/diagram_feedback_loop.txt` | `docs/assets/feedback_pipeline.png` | Feedback-Driven Context Pipeline |
| `docs/assets/diagram_trading_pipeline.txt` | `docs/assets/trading_pipeline.png` | SPY Iron Condor Trading Pipeline |

## To Add a New Diagram

1. Create a `.txt` file at `docs/assets/diagram_<name>.txt` with a detailed text description
2. Run `/update-diagrams`
3. Embed the generated PNG in README with `![Caption](docs/assets/<name>.png)`

## Implementation

The agent should:
1. Find all `docs/assets/diagram_*.txt` files
2. For each, check if the corresponding PNG exists (skip unless --force)
3. Run `uvx paperbanana generate` with GEMINI_API_KEY from .env
4. Copy outputs to target paths
5. Clean up run directories
6. Show all generated diagrams for review
7. Offer to commit the changes
