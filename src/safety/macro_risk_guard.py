"""
Macro Risk Guard - Tier 0 Safety Gate
Monitors macro-economic and geopolitical indicators (Oil, Treasury Yields)
to prevent trading during 'Black Swan' regime shifts.
Inspired by CNBC/PwC: 'Investors becoming more cautious on U.S. allocations'.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MacroRiskGuard:
    """
    Tier 0 Safety Gate that halts trading if macro-geopolitical risk spikes.
    """

    # Thresholds for 'Black Swan' alerts
    CRUDE_OIL_SPIKE_THRESHOLD: float = 0.08  # 8% move
    TREASURY_YIELD_SPIKE_THRESHOLD: float = 0.05  # 5% move in TNX
    OIL_CRISIS_PRICE: float = 100.0

    def __init__(self, data_client: Optional[Any] = None):
        """
        Args:
            data_client: Alpaca StockHistoricalDataClient instance
        """
        self.data_client = data_client

    def check_macro_vitals(self, macro_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Evaluates macro vitals. Returns (True, "") if safe, (False, reason) if blocked.
        """
        # 1. Check Geopolitical Oil Shock (CNBC/PwC takeaway #4)
        oil_change = macro_data.get("oil_change", 0.0)
        oil_price = macro_data.get("oil_price", 0.0)

        if abs(oil_change) > self.CRUDE_OIL_SPIKE_THRESHOLD or oil_price >= self.OIL_CRISIS_PRICE:
            reason = f"GEOPOLITICAL HALT: Oil volatility ({oil_change * 100:+.1f}%) or price (${oil_price:.2f})."
            logger.critical(f"🚨 {reason}")
            return False, reason

        # 2. Check Fiscal Deficit / Treasury Yields (CNBC/PwC takeaway #1)
        yield_change = macro_data.get("yield_change", 0.0)
        if abs(yield_change) > self.TREASURY_YIELD_SPIKE_THRESHOLD:
            reason = f"FISCAL RISK HALT: Treasury Yield volatility ({yield_change * 100:+.1f}%)."
            logger.critical(f"🚨 {reason}")
            return False, reason

        logger.info("✅ Macro vitals within normal parameters.")
        return True, ""

    def get_macro_snapshot(self) -> dict[str, Any]:
        """
        Autonomously fetches real-time USO and TNX data if client is available.
        Otherwise falls back to conservative defaults.
        """
        if not self.data_client:
            logger.warning("No data client provided to MacroRiskGuard - using baseline vitals.")
            return {"oil_price": 75.0, "oil_change": 0.0, "yield_change": 0.0}

        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame

            # USO acts as our Crude Oil proxy for the Alpha Engine
            # TNX acts as our 10-Year Treasury Yield proxy
            symbols = ["USO", "TNX"]

            # Fetch latest bars to calculate change
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=2)

            request_params = StockBarsRequest(
                symbol_or_symbols=symbols, timeframe=TimeFrame.Day, start=start
            )

            bars = self.data_client.get_stock_bars(request_params)

            snapshot = {"oil_price": 0.0, "oil_change": 0.0, "yield_change": 0.0}

            if "USO" in bars.data and len(bars.data["USO"]) >= 2:
                b = bars.data["USO"]
                current = b[-1].close
                prev = b[-2].close
                snapshot["oil_price"] = current
                snapshot["oil_change"] = (current - prev) / prev

            if "TNX" in bars.data and len(bars.data["TNX"]) >= 2:
                b = bars.data["TNX"]
                snapshot["yield_change"] = (b[-1].close - b[-2].close) / b[-2].close

            return snapshot

        except Exception as e:
            logger.error(f"Failed to fetch autonomous macro snapshot: {e}")
            return {"oil_price": 0.0, "oil_change": 0.0, "yield_change": 0.0}
