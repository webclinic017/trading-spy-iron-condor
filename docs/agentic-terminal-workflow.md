# Agentic Terminal Workflow

This repo now includes `scripts/agent_workflow_toolkit.py` to make terminal-based
agent operations faster, cleaner, and reproducible.

## What It Automates

- `zsh-snippet`: generates single-letter and helper shortcuts (`x`, `p`, `s`, `funked`)
- `slim-logs`: compresses noisy logs and redacts obvious secrets before LLM use
- `bundle`: builds token-budgeted context bundles from selected files/stdin
- `retro`: captures daily retros and writes a matching RAG lesson
- `chain`: runs planner -> executor command chaining with run artifacts

## Quick Start

```bash
python3 scripts/agent_workflow_toolkit.py zsh-snippet
```

Paste the output into `~/.zshrc`, then reload:

```bash
s
```

## Log Slimming

```bash
python3 scripts/agent_workflow_toolkit.py slim-logs --in artifacts/devloop/continuous.log --out artifacts/devloop/continuous.slim.log
```

Or stream from another command:

```bash
python3 scripts/system_health_check.py 2>&1 | python3 scripts/agent_workflow_toolkit.py slim-logs
```

## Context Bundling

```bash
python3 scripts/agent_workflow_toolkit.py bundle \
  README.md src/utils/llm_gateway.py tests/test_llm_gateway.py \
  --max-tokens 5000 \
  --out artifacts/devloop/context_bundle.md
```

Bundle CLI help or clipboard input with stdin:

```bash
python3 scripts/agent_workflow_toolkit.py bundle --include-stdin --stdin-name "tool-help.txt" <<'EOF'
my_tool --help output here
EOF
```

## Daily Retro (Auto-RAG)

```bash
python3 scripts/agent_workflow_toolkit.py retro \
  --win "CI stayed green after changes" \
  --friction "Incident logs were too noisy" \
  --action "Use slim-logs before diagnostics"
```

Artifacts written:

- `artifacts/devloop/retros/YYYY-MM-DD.md`
- `rag_knowledge/lessons_learned/ll_agentic_retro_YYYYMMDD.md`

You can also parse stdin lines with prefixes:

```bash
cat <<'EOF' | python3 scripts/agent_workflow_toolkit.py retro --include-stdin
WIN: Added cadence gate
FRICTION: Too much duplicate logging
ACTION: Keep a weekly no-trade diagnostic
EOF
```

## Planner -> Executor Chaining

Dry run:

```bash
python3 scripts/agent_workflow_toolkit.py chain \
  --task "Harden CI lint jobs" \
  --planner-cmd "cat" \
  --executor-cmd "cat" \
  --dry-run
```

Real run (example command placeholders):

```bash
python3 scripts/agent_workflow_toolkit.py chain \
  --task "Refactor blog generation pipeline" \
  --planner-cmd "claude --model opus" \
  --executor-cmd "codex"
```

Run artifacts are stored under `artifacts/agentic_runs/<timestamp>/`.
