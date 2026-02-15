# Generate Diagram - PaperBanana

Generate a publication-quality architecture diagram using PaperBanana (Gemini-powered).

## Usage

```
/generate-diagram <description> [--output <path>] [--caption <text>] [--iterations <n>]
```

## Arguments

- `description` (required): What to diagram — can be a text description or a file path to a .txt file
- `--output` (optional): Output PNG path (default: `docs/assets/<auto-slug>.png`)
- `--caption` (optional): Figure caption for the diagram (default: derived from description)
- `--iterations` (optional): Refinement rounds (default: 2)

## Examples

```
/generate-diagram "LLM gateway routing through TARS with fallback to OpenRouter"
/generate-diagram docs/assets/my_description.txt --output docs/assets/my_diagram.png --caption "System Architecture"
/generate-diagram "Iron condor execution pipeline with 6 safety gates" --iterations 3
```

## What It Does

1. Reads GEMINI_API_KEY from `.env` (maps to GOOGLE_API_KEY for PaperBanana)
2. If description is a file path, uses it directly; otherwise writes a temp .txt file
3. Runs `uvx paperbanana generate` with the given parameters
4. Copies final output to the target path
5. Cleans up temp/run directories
6. Shows the generated image for review

## Prerequisites

- `uvx` installed (comes with `uv`)
- `GEMINI_API_KEY` set in `.env`
- No pip install needed — uvx handles it

## Implementation

```bash
# Read Gemini key from .env
GEMINI_KEY=$(grep "GEMINI_API_KEY" .env | cut -d= -f2)

# Generate diagram
GOOGLE_API_KEY="$GEMINI_KEY" uvx paperbanana generate \
  --input "$INPUT_FILE" \
  --caption "$CAPTION" \
  --output "$OUTPUT_PATH" \
  --iterations "$ITERATIONS"
```

The agent should:
1. Parse the user's description argument
2. If it's not a file path, write it to a temp file at `docs/assets/_temp_description.txt`
3. Determine the output path (default: `docs/assets/<slugified-caption>.png`)
4. Run the paperbanana command with GEMINI_API_KEY from .env
5. Copy the `final_output.png` from the run directory to the target path
6. Clean up the run directory and temp file
7. Display the generated image using the Read tool
8. Ask if the user wants to embed it in the README
