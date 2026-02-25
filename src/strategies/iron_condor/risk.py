"""
Iron Condor Risk Layer
Role: Enforce Phil Town Rule #1 and Position Sizing.
"""

from typing import Dict, Any, List
import logging
from src.constants.trading_thresholds import RiskThresholds, PositionSizing

logger = logging.getLogger(__name__)

class IronCondorRisk:
    """
    Risk Guardian for Iron Condors.
    """
    
    def __init__(self, max_positions: int = 5):
        self.max_positions = max_positions
        self.stop_multiplier = RiskThresholds.IRON_CONDOR_STOP_LOSS_MULTIPLIER # 2.0

    def validate_exposure(self, positions: List[Any], ticker: str) -> bool:
        """
        MANDATORY FIRST STEP: Prevent race conditions and over-leverage.
        1 Iron Condor = 4 legs.
        """
        # Count option positions for this ticker
        ticker_options = [
            p for p in positions 
            if (hasattr(p, 'symbol') and p.symbol.startswith(ticker) and len(p.symbol) > 5) or
               (isinstance(p, dict) and p.get("symbol", "").startswith(ticker) and len(p.get("symbol", "")) > 5)
        ]
        
        total_contracts = sum(abs(int(float(getattr(p, 'qty', 0) if hasattr(p, 'qty') else p.get('qty', 0)))) for p in ticker_options)
        
        max_contracts = self.max_positions * 4
        current_ic_count = total_contracts // 4
        
        if total_contracts >= max_contracts:
            logger.warning(f"POSITION LIMIT: Already have {current_ic_count} ICs ({total_contracts} contracts)")
            return False
            
        logger.info(f"Position check OK: {current_ic_count}/{self.max_positions} ICs")
        return True

    def get_stop_prices(self, credit_received: float, short_put: float, short_call: float) -> Dict[str, float]:
        """
        Calculate stop prices based on 200% of credit received.
        """
        stop_offset = credit_received * (self.stop_multiplier - 1.0)
        return {
            "put_stop": short_put + stop_offset,
            "call_stop": short_call + stop_offset
        }
