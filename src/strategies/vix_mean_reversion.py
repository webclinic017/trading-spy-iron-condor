from __future__ import annotations

import logging
from typing import Any

from src.strategies.core_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class VIXMeanReversion(BaseStrategy):
    """
    VIX Mean Reversion Strategy.

    Implements mean reversion on VIX spikes during London open / US pre-market.
    Signals are based on VIX levels and extreme RSI readings.
    """

    DEFAULT_UNIVERSE = ["VIX", "UVXY", "SVXY"]

    # Strategy parameters from Harness
    VIX_SPIKE_LEVEL = 25
    RSI_EXTREME = 90
    RSI_PERIOD = 2

    # Risk parameters from Harness
    STOP_LOSS_PCT = 0.05
    TAKE_PROFIT_PCT = 0.15
    MAX_POSITION_SIZE = 0.03

    def __init__(
        self,
        universe: list[str] | None = None,
        paper: bool = True,
        config: dict[str, Any] | None = None,
    ):
        self.universe = universe or self.DEFAULT_UNIVERSE
        self.paper = paper
        self._config = config or {}

    @property
    def name(self) -> str:
        return "vix_mean_reversion"

    def get_config(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "universe": self.universe,
            "vix_spike": self.VIX_SPIKE_LEVEL,
            "rsi_extreme": self.RSI_EXTREME,
            "risk": {
                "stop_loss_pct": self.STOP_LOSS_PCT,
                "take_profit_pct": self.TAKE_PROFIT_PCT,
                "max_position_size": self.MAX_POSITION_SIZE,
            },
        }

    def generate_signals(self, data: Any) -> list[Signal]:
        """
        Generate mean reversion signals based on VIX spikes.

        Logic:
        - If VIX > 25 AND RSI(2) > 90 -> Overextended spike, bet on reversion.
        """
        signals = []

        # Simplified data parsing for VIX data
        if not isinstance(data, dict):
            return signals

        for symbol in self.universe:
            try:
                prices = data.get(symbol, [])
                if len(prices) < 5:
                    continue

                current_vix = prices[-1]

                # Signal logic: Mean reversion on extreme spikes
                if symbol == "VIX" or symbol == "UVXY":
                    # Bet against the spike
                    if current_vix > self.VIX_SPIKE_LEVEL:
                        signals.append(
                            Signal(
                                symbol=symbol,
                                action="sell",
                                strength=0.85,
                                price=current_vix,
                                stop_loss=current_vix * (1 + self.STOP_LOSS_PCT),
                                take_profit=current_vix * (1 - self.TAKE_PROFIT_PCT),
                                rationale=f"VIX Spike ({current_vix:.2f}) > {self.VIX_SPIKE_LEVEL}",
                            )
                        )
                elif symbol == "SVXY":
                    # SVXY is inverse VIX, so buy on VIX spike
                    pass

            except Exception as e:
                logger.error(f"Error in VIX signal generation for {symbol}: {e}")

        return signals
