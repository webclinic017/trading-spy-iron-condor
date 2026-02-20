"""Tests for RLHF trajectory storage helpers."""

from __future__ import annotations

import json
from pathlib import Path

from src.learning import rlhf_storage


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_store_trade_trajectory_legacy_signature(tmp_path, monkeypatch):
    trajectory_path = tmp_path / "feedback" / "trade_trajectories.jsonl"
    monkeypatch.setattr(rlhf_storage, "TRAJECTORY_PATH", trajectory_path)

    entry = rlhf_storage.store_trade_trajectory(
        order={"id": "ord-1", "symbol": "SPY", "side": "sell", "qty": 1, "filled_avg_price": 2.1},
        strategy="iron_condor",
        price=2.0,
    )

    rows = _read_rows(trajectory_path)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "entry"
    assert rows[0]["strategy"] == "iron_condor"
    assert rows[0]["order_id"] == "ord-1"
    assert rows[0]["price"] == 2.0
    assert entry["event_key"].startswith("trajectory::")


def test_store_trade_trajectory_structured_signature(tmp_path, monkeypatch):
    trajectory_path = tmp_path / "feedback" / "trade_trajectories.jsonl"
    monkeypatch.setattr(rlhf_storage, "TRAJECTORY_PATH", trajectory_path)

    entry = rlhf_storage.store_trade_trajectory(
        episode_id="ep-1",
        entry_state={"symbol": "SPY", "price": 600.0},
        action=2,
        exit_state={},
        reward=0.0,
        symbol="SPY",
        policy_version="1.0.0",
        metadata={"strategy": "iron_condor"},
    )

    rows = _read_rows(trajectory_path)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "entry"
    assert rows[0]["episode_id"] == "ep-1"
    assert rows[0]["strategy"] == "iron_condor"
    assert rows[0]["action"] == 2
    assert entry["event_key"].startswith("trajectory::")


def test_store_trade_outcome_writes_outcome_event(tmp_path, monkeypatch):
    trajectory_path = tmp_path / "feedback" / "trade_trajectories.jsonl"
    monkeypatch.setattr(rlhf_storage, "TRAJECTORY_PATH", trajectory_path)

    entry = rlhf_storage.store_trade_outcome(
        symbol="SPY",
        strategy="iron_condor",
        reward=42.5,
        won=True,
        exit_reason="PROFIT_TARGET",
        expiry="2026-03-20",
    )

    rows = _read_rows(trajectory_path)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "outcome"
    assert rows[0]["symbol"] == "SPY"
    assert rows[0]["reward"] == 42.5
    assert rows[0]["won"] is True
    assert entry["event_key"].startswith("trajectory::")
