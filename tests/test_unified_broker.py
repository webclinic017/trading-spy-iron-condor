"""Unit tests for canonical broker execution adapter."""

from __future__ import annotations

from types import SimpleNamespace

from src.execution.unified_broker import BrokerExecutionIntent, TradeGatewayBrokerAdapter


def test_trade_gateway_broker_adapter_rejects_with_codes() -> None:
    decision = SimpleNamespace(
        approved=False,
        rejection_reasons=[SimpleNamespace(name="MINIMUM_BATCH_NOT_MET", value="batch too small")],
        risk_score=0.9,
    )
    gateway = SimpleNamespace(
        evaluate=lambda _req: decision, execute=lambda _dec: {"id": "ignored"}
    )
    adapter = TradeGatewayBrokerAdapter(gateway)

    result = adapter.submit(BrokerExecutionIntent(symbol="SPY", side="buy", notional=10.0))

    assert not result.approved
    assert result.rejection_codes == ["MINIMUM_BATCH_NOT_MET"]
    assert result.rejection_reasons == ["batch too small"]


def test_trade_gateway_broker_adapter_executes_when_approved() -> None:
    decision = SimpleNamespace(approved=True, rejection_reasons=[], risk_score=0.1)
    order = {"id": "ord-1", "status": "filled", "symbol": "SPY"}
    gateway = SimpleNamespace(evaluate=lambda _req: decision, execute=lambda _dec: order)
    adapter = TradeGatewayBrokerAdapter(gateway)

    result = adapter.submit(BrokerExecutionIntent(symbol="SPY", side="buy", notional=100.0))

    assert result.approved
    assert result.order == order
    assert result.broker == "alpaca"
