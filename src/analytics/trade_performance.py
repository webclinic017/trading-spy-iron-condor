"""
Trade Performance Tracking Database

Jan 2026: Implements data-driven performance tracking for options trades.
Tracks every trade to calculate real win rate, profit factor, and expectancy.

Key Metrics:
- Win rate: Must be >80% for credit spread profitability (88% break-even)
- Profit factor: Sum of wins / Sum of losses (target >1.5)
- Expectancy: Average $ expected per trade
- Avg winner vs Avg loser ratio

Usage:
    from src.analytics.trade_performance import TradePerformanceTracker

    tracker = TradePerformanceTracker()
    tracker.record_trade({
        "symbol": "SPY",
        "strategy": "credit_spread",
        "entry_date": "2026-01-15",
        "entry_credit": 0.60,
        "exit_date": "2026-01-20",
        "exit_cost": 0.30,
        "result": "win"  # or "loss"
    })

    metrics = tracker.calculate_metrics()
    print(f"Win rate: {metrics['win_rate']:.1%}")
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Performance thresholds from CLAUDE.md math validation
WIN_RATE_BREAKEVEN = 0.88  # 88% needed for 7:1 risk/reward
WIN_RATE_TARGET = 0.80  # 80% target with early exits
PROFIT_FACTOR_TARGET = 1.5
MIN_TRADES_FOR_SIGNIFICANCE = 30  # Per LL-207


@dataclass
class TradeRecord:
    """Individual trade record for performance tracking."""

    trade_id: str
    symbol: str
    underlying: str
    strategy: Literal["credit_spread", "csp", "covered_call", "iron_condor"]
    entry_date: str
    entry_credit: float  # Credit received per share
    entry_collateral: float  # Total collateral required
    exit_date: str | None = None
    exit_cost: float | None = None  # Cost to close (per share)
    exit_reason: str | None = (
        None  # "profit_target", "stop_loss", "expiration", "manual"
    )
    result: Literal["win", "loss", "open"] = "open"
    pnl: float = 0.0  # Realized P/L
    days_held: int = 0
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics."""

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    open_trades: int = 0
    win_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0  # Expected $ per trade
    total_pnl: float = 0.0
    avg_days_held: float = 0.0
    is_profitable: bool = False
    meets_target_win_rate: bool = False
    sample_size_adequate: bool = False
    calculated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TradePerformanceTracker:
    """
    Track and analyze options trading performance.

    Stores trades in JSON for simplicity and auditability.
    Calculates key metrics needed to validate strategy profitability.
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize tracker with data directory."""
        self.data_dir = data_dir or Path("/home/user/trading/data/trades")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trade_history.json"
        self.metrics_file = self.data_dir / "performance_metrics.json"
        self.trades: list[TradeRecord] = []
        self._load_trades()

    def _load_trades(self) -> None:
        """Load existing trades from disk."""
        if self.trades_file.exists():
            try:
                with open(self.trades_file) as f:
                    data = json.load(f)
                self.trades = [TradeRecord(**t) for t in data]
                logger.info(f"Loaded {len(self.trades)} trades from {self.trades_file}")
            except Exception as e:
                logger.warning(f"Failed to load trades: {e}")
                self.trades = []

    def _save_trades(self) -> None:
        """Persist trades to disk."""
        try:
            with open(self.trades_file, "w") as f:
                json.dump([asdict(t) for t in self.trades], f, indent=2)
            logger.debug(f"Saved {len(self.trades)} trades to {self.trades_file}")
        except Exception as e:
            logger.error(f"Failed to save trades: {e}")

    def record_trade(self, trade_data: dict) -> TradeRecord:
        """
        Record a new trade.

        Args:
            trade_data: Dict with trade details (symbol, strategy, entry_date, etc.)

        Returns:
            TradeRecord object
        """
        # Generate trade ID if not provided
        if "trade_id" not in trade_data:
            trade_data["trade_id"] = (
                f"{trade_data['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        # Extract underlying from option symbol if needed
        if "underlying" not in trade_data:
            trade_data["underlying"] = trade_data["symbol"][:3]  # Simple extraction

        trade = TradeRecord(**trade_data)
        self.trades.append(trade)
        self._save_trades()

        logger.info(
            f"Recorded trade: {trade.trade_id} ({trade.strategy} on {trade.symbol})"
        )
        return trade

    def close_trade(
        self,
        trade_id: str,
        exit_date: str,
        exit_cost: float,
        exit_reason: str = "manual",
    ) -> TradeRecord | None:
        """
        Close an open trade and calculate P/L.

        Args:
            trade_id: ID of trade to close
            exit_date: Date of exit
            exit_cost: Cost to close (per share)
            exit_reason: Why closed (profit_target, stop_loss, expiration, manual)

        Returns:
            Updated TradeRecord or None if not found
        """
        for trade in self.trades:
            if trade.trade_id == trade_id and trade.result == "open":
                trade.exit_date = exit_date
                trade.exit_cost = exit_cost
                trade.exit_reason = exit_reason

                # Calculate P/L: For credit spreads, profit = credit - cost to close
                trade.pnl = (trade.entry_credit - exit_cost) * 100  # Per contract
                trade.result = "win" if trade.pnl > 0 else "loss"

                # Calculate days held
                try:
                    entry = datetime.fromisoformat(trade.entry_date)
                    exit_dt = datetime.fromisoformat(exit_date)
                    trade.days_held = (exit_dt - entry).days
                except ValueError:
                    trade.days_held = 0

                self._save_trades()
                logger.info(
                    f"Closed trade {trade_id}: {trade.result.upper()} "
                    f"P/L=${trade.pnl:.2f} ({exit_reason})"
                )
                return trade

        logger.warning(f"Trade {trade_id} not found or already closed")
        return None

    def calculate_metrics(self) -> PerformanceMetrics:
        """
        Calculate performance metrics from trade history.

        Returns:
            PerformanceMetrics with win rate, profit factor, expectancy, etc.
        """
        closed_trades = [t for t in self.trades if t.result != "open"]
        open_trades = [t for t in self.trades if t.result == "open"]

        wins = [t for t in closed_trades if t.result == "win"]
        losses = [t for t in closed_trades if t.result == "loss"]

        total_wins = sum(t.pnl for t in wins)
        total_losses = abs(sum(t.pnl for t in losses))

        metrics = PerformanceMetrics(
            total_trades=len(closed_trades),
            wins=len(wins),
            losses=len(losses),
            open_trades=len(open_trades),
            total_pnl=sum(t.pnl for t in closed_trades),
        )

        if closed_trades:
            metrics.win_rate = len(wins) / len(closed_trades)
            metrics.avg_days_held = sum(t.days_held for t in closed_trades) / len(
                closed_trades
            )

        if wins:
            metrics.avg_winner = total_wins / len(wins)

        if losses:
            metrics.avg_loser = total_losses / len(losses)

        if total_losses > 0:
            metrics.profit_factor = total_wins / total_losses
        elif total_wins > 0:
            metrics.profit_factor = float("inf")

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        if closed_trades:
            metrics.expectancy = (metrics.win_rate * metrics.avg_winner) - (
                (1 - metrics.win_rate) * metrics.avg_loser
            )

        # Validation checks
        metrics.is_profitable = metrics.total_pnl > 0
        metrics.meets_target_win_rate = metrics.win_rate >= WIN_RATE_TARGET
        metrics.sample_size_adequate = len(closed_trades) >= MIN_TRADES_FOR_SIGNIFICANCE

        # Save metrics
        self._save_metrics(metrics)

        return metrics

    def _save_metrics(self, metrics: PerformanceMetrics) -> None:
        """Persist metrics to disk."""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(asdict(metrics), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def get_summary(self) -> str:
        """Get human-readable performance summary."""
        metrics = self.calculate_metrics()

        status = "PROFITABLE" if metrics.is_profitable else "NOT PROFITABLE"
        win_rate_status = (
            "OK"
            if metrics.meets_target_win_rate
            else f"BELOW {WIN_RATE_TARGET:.0%} TARGET"
        )
        sample_status = (
            "ADEQUATE"
            if metrics.sample_size_adequate
            else f"NEED {MIN_TRADES_FOR_SIGNIFICANCE} TRADES"
        )

        return f"""
═══════════════════════════════════════════════════════════
📊 TRADE PERFORMANCE SUMMARY
═══════════════════════════════════════════════════════════
Status: {status}
Total Trades: {metrics.total_trades} ({metrics.open_trades} open)
Win Rate: {metrics.win_rate:.1%} ({win_rate_status})
Sample Size: {sample_status}

Wins: {metrics.wins} | Losses: {metrics.losses}
Avg Winner: ${metrics.avg_winner:.2f}
Avg Loser: ${metrics.avg_loser:.2f}
Profit Factor: {metrics.profit_factor:.2f}
Expectancy: ${metrics.expectancy:.2f}/trade

Total P/L: ${metrics.total_pnl:.2f}
Avg Days Held: {metrics.avg_days_held:.1f}
═══════════════════════════════════════════════════════════
"""


# Convenience function
def get_performance_tracker() -> TradePerformanceTracker:
    """Get TradePerformanceTracker instance."""
    return TradePerformanceTracker()


if __name__ == "__main__":
    """Example usage and testing."""
    logging.basicConfig(level=logging.INFO)

    tracker = TradePerformanceTracker()
    print(tracker.get_summary())
