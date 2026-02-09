"""RLHF trade trajectory storage for learning and audits."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

TRAJECTORY_PATH = Path("data/feedback/trade_trajectories.jsonl")


def store_trade_trajectory(order: dict[str, Any], strategy: str, price: float) -> dict[str, Any]:
    """Persist a trade trajectory entry as JSONL.

    Args:
        order: Order payload from broker executor.
        strategy: Strategy label for the trade.
        price: Executed price.

    Returns:
        The written entry.
    """
    TRAJECTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "strategy": strategy,
        "symbol": order.get("symbol"),
        "side": order.get("side"),
        "qty": order.get("qty"),
        "price": price,
        "order_id": order.get("id"),
        "source": "alpaca_executor",
    }

    with TRAJECTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry
