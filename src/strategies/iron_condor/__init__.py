"""
Iron Condor Vertical Slice Controller
Orchestrates Signal -> Risk -> Execution.
"""

import logging
from typing import Any

from .executor import IronCondorExecutor
from .risk import IronCondorRisk
from .signal import IronCondorSignal

logger = logging.getLogger(__name__)


class IronCondorController:
    """
    Vertical Slice Controller for Iron Condors.
    """

    def __init__(self, trading_client):
        self.signal = IronCondorSignal()
        self.risk = IronCondorRisk()
        self.executor = IronCondorExecutor(trading_client)

    def run_cycle(
        self, market_data: dict[str, Any], account_info: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute one full cycle of the strategy.
        """
        symbol = market_data.get("symbol", "SPY")

        # 1. SIGNAL
        signal_result = self.signal.generate_signal(market_data)
        if not signal_result.should_entry:
            return {"status": "SKIPPED", "reason": signal_result.reason}

        # 2. RISK & POSITION SIZING
        positions = account_info.get("positions", [])

        if not self.risk.validate_exposure(positions, symbol):
            return {"status": "SKIPPED", "reason": "Max exposure reached for ticker"}

        # 3. EXECUTION
        # Note: In production, the signal layer would provide actual symbols from a chain provider.
        # This is a structural demonstration.
        try:
            # qty = self.risk.calculate_quantity(equity, max_risk=1000)
            # order = self.executor.build_mleg_order(symbol, legs, qty)
            # result = self.executor.execute(order)
            return {
                "status": "READY_TO_TRADE",
                "signal": signal_result.reason,
                "confidence": signal_result.confidence,
            }
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"status": "ERROR", "error": str(e)}
