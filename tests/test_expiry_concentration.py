"""Tests for expiry concentration guard in TradeGateway.

Prevents >40% of ICs in a single expiry week (ISO week grouping).
One bad week shouldn't wipe everything.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.risk.trade_gateway import TradeGateway


def _make_ic_positions(expiry_yymmdd_list: list[str]) -> list[dict]:
    """Build mock option positions for given expiries.

    Each expiry gets 4 legs (long put, short put, short call, long call).
    """
    positions = []
    for exp in expiry_yymmdd_list:
        for leg_type, strike, qty in [
            ("P", "00640000", "1"),
            ("P", "00650000", "-1"),
            ("C", "00720000", "-1"),
            ("C", "00730000", "1"),
        ]:
            positions.append({
                "symbol": f"SPY{exp}{leg_type}{strike}",
                "qty": qty,
                "market_value": "100",
                "unrealized_pl": "10",
            })
    return positions


class TestExpiryConcentration:
    """Expiry concentration: max 40% of ICs in one ISO week."""

    def _make_gateway(self):
        gw = TradeGateway.__new__(TradeGateway)
        gw.executor = None
        gw.paper = True
        gw.recent_trades = []
        gw.accumulated_cash = 0.0
        gw.last_accumulation_date = None
        gw.daily_pnl = 0.0
        gw.daily_pnl_date = None
        gw.peak_equity = 100_000.0
        gw.capital_calculator = MagicMock()
        gw.rag = MagicMock()
        gw.rag.query.return_value = []
        gw.state_file = Path("/dev/null")
        return gw

    def test_no_positions_passes(self):
        gw = self._make_gateway()
        passed, msg = gw._check_expiry_concentration([])
        assert passed is False  # False = not blocked
        assert msg == ""

    def test_all_same_week_with_3_ics_blocked(self):
        """3 ICs all in same week = 100% concentration -> blocked."""
        positions = _make_ic_positions(["260320", "260320", "260320"])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is True
        assert "100" in msg or "concentration" in msg.lower()

    def test_spread_across_weeks_passes(self):
        """3 ICs across 3 different weeks = 33% each -> passes."""
        positions = _make_ic_positions(["260313", "260320", "260327"])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is False

    def test_two_of_three_in_same_week_passes(self):
        """2 of 3 ICs in same week = 67% -> blocked (>40%)."""
        positions = _make_ic_positions(["260320", "260320", "260327"])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is True

    def test_exactly_at_threshold(self):
        """2 of 5 in same week = 40% -> not blocked (at threshold, not over)."""
        positions = _make_ic_positions([
            "260313", "260320", "260320", "260327", "260403"
        ])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is False

    def test_one_ic_never_blocked(self):
        """Single IC can't be over-concentrated."""
        positions = _make_ic_positions(["260320"])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is False

    def test_iso_week_groups_fri_and_wed_same_week(self):
        """March 18 (Wed) and March 20 (Fri) are same ISO week -> grouped."""
        # 260318 = Wed, 260320 = Fri — same ISO week 12
        positions = _make_ic_positions(["260318", "260320", "260327"])
        gw = self._make_gateway()
        blocked, msg = gw._check_expiry_concentration(positions)
        assert blocked is True  # 2/3 = 67% in week 12
