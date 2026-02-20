"""Tests for TradeMemory persistence and query behavior."""

from __future__ import annotations

from src.learning.trade_memory import TradeMemory


def test_trade_memory_query_returns_real_stats(tmp_path):
    memory = TradeMemory(memory_path=tmp_path / "trade_memory.json")
    memory.add_trade(
        {
            "symbol": "SPY",
            "strategy": "iron_condor",
            "entry_reason": "high_iv",
            "won": True,
            "pnl": 50.0,
        }
    )
    memory.add_trade(
        {
            "symbol": "SPY",
            "strategy": "iron_condor",
            "entry_reason": "high_iv",
            "won": False,
            "pnl": -20.0,
        }
    )
    memory.add_trade(
        {
            "symbol": "SPY",
            "strategy": "iron_condor",
            "entry_reason": "high_iv",
            "won": True,
            "pnl": 40.0,
        }
    )

    result = memory.query_similar("iron_condor", "high_iv", symbol="SPY")
    assert result["found"] is True
    assert result["sample_size"] == 3
    assert result["wins"] == 2
    assert result["losses"] == 1
    assert round(result["win_rate"], 4) == round(2 / 3, 4)
    assert round(result["total_pnl"], 2) == 70.0


def test_trade_memory_persists_and_reloads(tmp_path):
    path = tmp_path / "trade_memory.json"
    memory = TradeMemory(memory_path=path)
    memory.add_trade(
        {
            "symbol": "QQQ",
            "strategy": "iron_condor",
            "entry_reason": "range_bound",
            "won": False,
            "pnl": -33.0,
        }
    )

    reloaded = TradeMemory(memory_path=path)
    result = reloaded.query_similar("iron_condor", "range_bound", symbol="QQQ")
    assert result["found"] is True
    assert result["sample_size"] == 1
    assert result["wins"] == 0
    assert result["losses"] == 1
