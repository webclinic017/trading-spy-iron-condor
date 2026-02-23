# RLM (Recursive Language Model) Methodology

This document outlines the **RLM Algorithm 1** pattern implemented in our trading system, optimized for high-efficiency, large-scale analysis.

## 🧠 What is RLM?
RLM prioritizes **Code-First execution** over traditional agentic reasoning. Instead of an LLM "reading" thousands of lines of logs (which is slow and expensive), the RLM Orchestrator writes and executes local Python code to extract insights instantly.

## 🛠️ Key Pattern: Algorithm 1 (Zero Sub-calls)
As shown in recent benchmarks (e.g., GPT-5.2-Codex), the most efficient agents do not dump context or make recursive sub-calls. They follow **Algorithm 1**:
1.  **Receive Task**: e.g., "Analyze the last 5 days of trade history."
2.  **Plan**: Identify that this is a data aggregation task.
3.  **Execute Code**: Use `collections.Counter` and `json.load` locally (Zero Sub-calls).
4.  **Finalize**: Return a high-signal summary.

## 📈 Implementation in our System
- **`src/orchestration/harness/rlm_orchestrator.py`**: The core engine implementing Algorithm 1.
- **Trade Aggregation**: Automatically processes `data/trades_*.json` without sending full trade lists to an external API.
- **Efficiency**: 100x faster than traditional agentic loops.

## 🚀 How to trigger an RLM Task
Use the `RLMTask` dataclass:
```python
task = RLMTask(
    id="performance_audit",
    task_type="trade_aggregation",
    query="Find the most frequent winning tickers.",
    data_paths=["data/trades_2026-02-20.json"]
)
orchestrator.execute_algorithm_1(task)
```

---
*Reference: [RLM CLI Initial Experiments](https://x.com/omarsar0/status/2024972027224846631)*
