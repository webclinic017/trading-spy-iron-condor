# Prompt: Create New Trading Strategy (/new-strategy)
Goal: Generate a complete vertical slice for a new trading strategy following the **Folder-as-Namespace** pattern.

## Parameters
- **Strategy Name:** {{strategyName}} (PascalCase, e.g., "IronCondor")
- **Ticker Focus:** {{ticker}} (e.g., "SPY")
- **Target DTE:** {{dte}} (e.g., "30-45")

## Core Instructions
Please generate the code blocks for these 4 layers using our modular architecture.
*Note: Logic files and folders must be snake_case in Python.*

---

### 1. Alpha/Signal Layer
**File:** `src/strategies/{{strategyName.lower()}}/signal.py`
- **Role:** Define entry/exit signals (e.g., VIX Mean Reversion, Momentum).
- **Requirements:** Must return a `SignalResult` with confidence and reasoning.

### 2. Execution Layer
**File:** `src/strategies/{{strategyName.lower()}}/executor.py`
- **Role:** Handle Alpaca order submission.
- **Requirements:** Must use `src.safety.mandatory_trade_gate.safe_submit_order`.

### 3. Risk & Sizing Layer
**File:** `src/strategies/{{strategyName.lower()}}/risk.py`
- **Role:** Define strategy-specific stop-losses and position sizing.
- **Requirements:** Must enforce Phil Town Rule #1 (Mandatory Stops).

### 4. Verification Layer
**File:** `src/strategies/{{strategyName.lower()}}/__tests__/test_strategy.py`
- **Role:** Automated smoke tests.
- **Requirements:** 100% pass on synthetic data before live deployment.

---

## Governance Rules
1. **No Hardcoding:** All thresholds must be in `src/constants/trading_thresholds.py`.
2. **Mandatory Logging:** Every decision must be logged to `OrchestratorTelemetry`.
3. **Fail-Safe:** If any leg of a multi-leg trade fails, the entire order must be cancelled (MLEG).
