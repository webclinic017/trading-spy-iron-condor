"""
Macro Risk Guard - Tier 0 Safety Gate
Monitors macro-economic and geopolitical indicators (Oil, Treasury Yields)
to prevent trading during 'Black Swan' regime shifts.
Inspired by CNBC/PwC: 'Investors becoming more cautious on U.S. allocations'.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

class MacroRiskGuard:
    """
    Tier 0 Safety Gate that halts trading if macro-geopolitical risk spikes.
    """

    # Thresholds for 'Black Swan' alerts
    CRUDE_OIL_SPIKE_THRESHOLD = 0.08  # 8% intraday or multi-day spike
    TREASURY_YIELD_SPIKE_THRESHOLD = 0.05 # 5% move in TNX

    def __init__(self, trading_client=None):
        self.client = trading_client

    def check_macro_vitals(self, macro_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Evaluates macro vitals. Returns (True, "") if safe, (False, reason) if blocked.
        Indicators:
        - USO (Crude Oil ETF) or CL (Futures)
        - TNX (10-Year Treasury Yield)
        """
        # 1. Check Geopolitical Oil Shock (CNBC/PwC takeaway #4)
        oil_change = macro_data.get("oil_change", 0.0)
        oil_price = macro_data.get("oil_price", 0.0)

        if oil_change > self.CRUDE_OIL_SPIKE_THRESHOLD or oil_price >= 100.0:
            reason = f"GEOPOLITICAL HALT: Oil spike detected ({oil_change*100:.1f}%). Risk of inflationary shock."
            logger.critical(f"🚨 {reason}")
            return False, reason

        # 2. Check Fiscal Deficit / Treasury Yields (CNBC/PwC takeaway #1)
        yield_change = macro_data.get("yield_change", 0.0)
        if abs(yield_change) > self.TREASURY_YIELD_SPIKE_THRESHOLD:
            reason = f"FISCAL RISK HALT: Treasury Yield volatility ({yield_change*100:.1f}%). Market derating U.S. assets."
            logger.critical(f"🚨 {reason}")
            return False, reason

        logger.info("✅ Macro vitals within normal parameters.")
        return True, ""

    def get_macro_snapshot(self) -> dict[str, Any]:
        """
        In production, this would fetch USO and TNX from Alpaca or Polygon.
        For the MVP, we provide a placeholder data structure.
        """
        # Placeholder for real-time integration
        return {
            "oil_price": 78.50,
            "oil_change": 0.01,
            "yield_change": 0.005
        }
