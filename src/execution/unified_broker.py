"""Canonical broker execution adapter used by orchestrator execution stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.risk.trade_gateway import TradeRequest


@dataclass(frozen=True)
class BrokerExecutionIntent:
    """Canonical execution intent."""

    symbol: str
    side: str
    notional: float | None = None
    quantity: float | None = None
    source: str = "orchestrator"


@dataclass
class BrokerExecutionResult:
    """Canonical broker execution result."""

    approved: bool
    broker: str
    order: dict[str, Any] | None = None
    rejection_reasons: list[str] = field(default_factory=list)
    rejection_codes: list[str] = field(default_factory=list)
    risk_score: float = 0.0


class TradeGatewayBrokerAdapter:
    """Broker adapter that enforces risk checks through TradeGateway."""

    def __init__(self, trade_gateway: Any, broker_name: str = "alpaca") -> None:
        self.trade_gateway = trade_gateway
        self.broker_name = broker_name

    def submit(self, intent: BrokerExecutionIntent) -> BrokerExecutionResult:
        request = TradeRequest(
            symbol=intent.symbol,
            side=intent.side,
            notional=intent.notional,
            quantity=intent.quantity,
            source=intent.source,
        )
        decision = self.trade_gateway.evaluate(request)
        if not decision.approved:
            return BrokerExecutionResult(
                approved=False,
                broker=self.broker_name,
                rejection_reasons=[reason.value for reason in decision.rejection_reasons],
                rejection_codes=[reason.name for reason in decision.rejection_reasons],
                risk_score=decision.risk_score,
            )
        order = self.trade_gateway.execute(decision)
        return BrokerExecutionResult(
            approved=True,
            broker=self.broker_name,
            order=order or {},
            risk_score=decision.risk_score,
        )
