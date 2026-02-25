# AI Engineering Governance: Python
When working inside the Python trading system, AI agents must follow these rules:

## 1. Architectural Integrity
- All strategies must follow the **Vertical Slice** pattern: `signal.py`, `risk.py`, `executor.py`.
- No strategy logic is allowed in `scripts/` (scripts are for orchestration only).
- All shared utilities must reside in `src/core` or `src/utils`.

## 2. Safety & Risk (Mandatory)
- **Phil Town Rule #1**: Every opening order MUST have a stop-loss attached.
- Never bypass `src/safety/mandatory_trade_gate.py`.
- Position sizing is capped at 5% per trade.

## 3. Formatting & Quality
- Indentation: 4 spaces.
- Documentation: Every class/method requires a docstring explaining its role in the Alpha Engine.
- Typing: Use type hints for all public interfaces.

## 4. Auditor Compliance
- All new modules must pass `scripts/audit_strategy.py` before being considered "Tested and Proved".
