# Unsloth Integration for Local LLMs

This document outlines the roadmap and setup for using Unsloth with Claude Code and local model fine-tuning for our trading system.

## 🚀 High-ROI Objectives
1. **IP Protection**: Run agentic coding tasks locally on Apple Silicon (Metal) via `llama.cpp`.
2. **Cost Reduction**: Minimize Anthropic API token costs by using open models (DeepSeek, Qwen) for routine tasks.
3. **Specialization**: Fine-tune models on our 177+ proprietary trading files (strategies, backtest logic, execution engine).

---

## 🛠️ Local Setup (Inference)

### 1. Requirements
- Apple Silicon Mac (M1/M2/M3)
- `llama.cpp` (installed via `brew install llama.cpp`)
- Claude Code

### 2. Configure Environment
Source our local LLM config to redirect Claude Code:
```bash
source config/local_llm_config.sh
enable_local_claude
```

### 3. Start Local Server
Download an Unsloth Dynamic GGUF (e.g., DeepSeek-Coder-V2) and start the server:
```bash
# In config/local_llm_config.sh
start_local_server /path/to/unsloth_model.gguf
```

---

## 🧠 Model Specialization (Fine-tuning)

### 1. Prepare Dataset
We have automated the collection of our codebase for fine-tuning:
```bash
python3 scripts/collect_unsloth_dataset.py
```
**Output**: `data/ml_training_data/trading_specialization_dataset.json`

### 2. Fine-tuning with Unsloth
Unsloth allows 2x faster training and 70% less VRAM. Use the following notebook pattern:
- Base Model: `unsloth/deepseek-coder-v2-lite-instruct-bnb-4bit`
- Dataset: `data/ml_training_data/trading_specialization_dataset.json`
- Target: Learn the architecture of our `src/` directory and strategy patterns in `config/`.

---

## 📊 Business ROI Summary
- **Data Security**: Strategy logic (`strategies.yaml`) never leaves our local environment.
- **Latency**: Local inference on Metal is often faster than API round-trips for large prompts.
- **Developer Productivity**: Claude Code becomes a "Domain Expert" by training on our specific code patterns.
