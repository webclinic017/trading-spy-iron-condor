#!/bin/bash

# Configuration for Local LLM (Unsloth GGUFs) via llama.cpp
# This allows Claude Code to run locally on Apple Silicon (Metal)
# Reference: https://unsloth.ai/docs/basics/claude-code

# Default Local Port for llama-server
export LOCAL_LLM_PORT=8080
export LOCAL_LLM_HOST="localhost"
export LOCAL_LLM_URL="http://$LOCAL_LLM_HOST:$LOCAL_LLM_PORT/v1"

# Function to point Claude Code to Local Unsloth Model
enable_local_claude() {
    export ANTHROPIC_BASE_URL="$LOCAL_LLM_URL"
    echo "✅ Claude Code now routing to LOCAL Unsloth Model ($LOCAL_LLM_URL)"
    echo "⚠️  Ensure 'llama-server' is running with a GGUF model."
}

# Function to reset Claude Code to Anthropic API
disable_local_claude() {
    unset ANTHROPIC_BASE_URL
    echo "✅ Claude Code now routing to ANTHROPIC API (Cloud)"
}

# Function to start llama-server (on Apple Silicon)
# Requires llama.cpp installed: brew install llama.cpp
start_local_server() {
    local model_path=$1
    if [ -z "$model_path" ]; then
        echo "❌ Error: Please provide path to a GGUF model file."
        return 1
    fi
    
    echo "🚀 Starting llama-server with model: $model_path"
    # Using -ngl 99 to ensure all layers run on GPU (Apple Metal)
    llama-server -m "$model_path" --port "$LOCAL_LLM_PORT" --ngl 99 --ctx-size 8192
}

# Usage Instructions
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Usage: source config/local_llm_config.sh"
    echo "Then run: enable_local_claude or disable_local_claude"
fi
