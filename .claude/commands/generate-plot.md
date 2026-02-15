# Generate Plot - PaperBanana

Generate a publication-quality statistical plot/chart using PaperBanana (Gemini-powered).

## Usage

```
/generate-plot <data-file> [--intent <description>] [--output <path>]
```

## Arguments

- `data-file` (required): Path to CSV/JSON data file
- `--intent` (optional): What the chart should show (e.g., "Bar chart comparing model costs")
- `--output` (optional): Output PNG path (default: `docs/assets/<auto-slug>.png`)

## Examples

```
/generate-plot data/feedback/stats.json --intent "RLHF satisfaction rate over time"
/generate-plot data/system_state.json --intent "Account equity progression"
/generate-plot data/model_costs.csv --intent "Cost per model tier comparison"
```

## What It Does

1. Reads GEMINI_API_KEY from `.env`
2. Runs `uvx paperbanana plot` with the data file and intent
3. Copies output to target path
4. Cleans up temp directories
5. Shows the generated plot for review

## Implementation

```bash
GEMINI_KEY=$(grep "GEMINI_API_KEY" .env | cut -d= -f2)

GOOGLE_API_KEY="$GEMINI_KEY" uvx paperbanana plot \
  --data "$DATA_FILE" \
  --intent "$INTENT"
```

The agent should:
1. Verify the data file exists and is valid CSV or JSON
2. Run paperbanana plot with the Gemini key from .env
3. Copy output to target path
4. Display the generated plot
5. Ask if the user wants to embed it in the README or a blog post
