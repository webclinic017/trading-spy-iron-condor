import json
import os
from datetime import datetime

# Performance Monitor for Local vs Cloud LLM
# Tracks token usage (approximated), latency, and cost savings.

LOG_FILE = "data/performance_log.json"
CLOUD_TOKEN_PRICE = 0.015 / 1000  # Example price for Anthropic Claude 3.5 Sonnet (per k-token)


def log_inference(model_name, is_local, tokens_in, tokens_out, latency_ms):
    """
    Logs an inference event to data/performance_log.json
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    cost_saved = 0
    if is_local:
        # Calculate what this WOULD have cost in the cloud
        cost_saved = (tokens_in + tokens_out) * CLOUD_TOKEN_PRICE

    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "is_local": is_local,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "cost_saved_usd": round(cost_saved, 6),
    }

    # Read existing logs or start new
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    if is_local:
        print(f"💰 Saved ${cost_saved:.6f} by running locally on Unsloth!")
    print(f"⏱️  Latency: {latency_ms}ms | Model: {model_name}")


if __name__ == "__main__":
    # Example usage for manual testing
    print("🚀 Local LLM ROI Monitor Initialized")
    log_inference("DeepSeek-Coder-V2 (Local)", True, 500, 200, 1250)
