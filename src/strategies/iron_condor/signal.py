"""
Iron Condor Signal Layer
Role: Define entry/exit signals based on market conditions.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta
from src.signals.vix_mean_reversion_signal import VIXMeanReversionSignal
from src.constants.trading_thresholds import RiskThresholds

logger = logging.getLogger(__name__)

@dataclass
class SignalResult:
    should_entry: bool
    confidence: float
    reason: str
    metadata: Dict[str, Any]

class IronCondorSignal:
    """
    Alpha Engine for Iron Condors.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "underlying": "SPY",
            "target_dte": 30,
            "short_delta": 0.15,
            "wing_width": 10
        }

    def check_entry_conditions(self) -> Tuple[bool, str, float]:
        """
        Check if conditions are right for entry using VIX Mean Reversion.
        """
        try:
            vix_signal = VIXMeanReversionSignal()
            signal = vix_signal.calculate_signal()

            if signal.signal == "OPTIMAL_ENTRY":
                return True, f"OPTIMAL: {signal.reason}", signal.confidence
            if signal.signal == "GOOD_ENTRY":
                return True, f"GOOD: {signal.reason}", signal.confidence
            if signal.signal == "AVOID":
                return False, signal.reason, 0.0
                
            # NEUTRAL: Fall through to legacy check
        except Exception as e:
            logger.warning(f"VIX Signal failed: {e}")

        # Legacy fallback
        return False, "Neutral or failed VIX signal", 0.0

    def calculate_expiry(self) -> str:
        """Calculate expiry - MUST be a Friday."""
        target_date = datetime.now() + timedelta(days=self.config["target_dte"])
        days_until_friday = (4 - target_date.weekday()) % 7
        if days_until_friday == 0 and target_date.weekday() != 4:
            days_until_friday = 7
        expiry_date = target_date + timedelta(days=days_until_friday)
        
        if (expiry_date - datetime.now()).days < 21:
            expiry_date += timedelta(days=7)
            
        return expiry_date.strftime("%Y-%m-%d")

    def generate_signal(self, market_data: Dict[str, Any]) -> SignalResult:
        """
        Main entry point for signal generation.
        """
        should_trade, reason, confidence = self.check_entry_conditions()
        
        expiry = self.calculate_expiry()
        
        return SignalResult(
            should_entry=should_trade,
            confidence=confidence,
            reason=reason,
            metadata={
                "expiry": expiry,
                "underlying": self.config["underlying"],
                "target_dte": self.config["target_dte"]
            }
        )
