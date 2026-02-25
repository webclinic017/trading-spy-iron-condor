"""
Observability Agent
Proactively identifies bugs and system issues before they impact performance.
"""

import logging
from typing import List, Dict, Any
from src.monitoring.telemetry_gateway import TelemetryGateway

logger = logging.getLogger(__name__)

class ObservabilityAgent:
    """
    Monitors OTel spans to detect 'Execution Mismatches' and 'Agent Drift'.
    """
    
    def __init__(self):
        self.gateway = TelemetryGateway()

    def audit_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Analyzes a specific trace for operational integrity.
        """
        spans = self.gateway.get_traces_for_id(trace_id)
        names = [s["name"] for s in spans]
        
        # Scenario 1: Execution Mismatch
        # If 'order_submitted' exists but 'order_filled' or 'order_confirmed' is missing
        if "order_submitted" in names:
            if not any(n in names for n in ["order_filled", "order_confirmed"]):
                logger.critical(f"🚨 EXECUTION MISMATCH DETECTED: Order {trace_id} submitted but no fill confirmed.")
                return {"healthy": False, "issue": "UNFILLED_ORDER"}
        
        # Scenario 2: Juror Bypass
        if "strategy_entry" in names and "juror_consensus" not in names:
            logger.warning(f"⚠️ GOVERNANCE VIOLATION: Juror check bypassed for {trace_id}.")
            return {"healthy": False, "issue": "JUROR_BYPASS"}

        logger.info(f"✅ Trace {trace_id} audited: No operational issues found.")
        return {"healthy": True}

    def scan_recent_activity(self, limit: int = 100):
        """
        Scans recent logs for common failure patterns.
        """
        # In a real implementation, this would aggregate logs and look for spikes in failures
        pass
