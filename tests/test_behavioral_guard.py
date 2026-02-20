"""Tests for BehavioralGuard — FOMO, stop-loss cooling, and blacklist checks."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.safety.behavioral_guard import BehavioralGuard


class TestFOMOCheck:
    """FOMO: reject when SPY moved >2% intraday."""

    def test_large_move_blocks(self):
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=0.025)
        assert result.passed is False
        assert any("FOMO" in r for r in result.rejections)

    def test_small_move_allows(self):
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=0.005)
        assert not any("FOMO" in r for r in result.rejections)

    def test_negative_large_move_blocks(self):
        """Negative moves (selloff) also inflate premiums."""
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=-0.03)
        assert result.passed is False
        assert any("FOMO" in r for r in result.rejections)

    def test_no_data_fails_open(self):
        """When SPY data unavailable, allow trade (other gates protect)."""
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=None)
        assert not any("FOMO" in r for r in result.rejections)
        assert any("skipped" in w.lower() for w in result.warnings)

    def test_exactly_at_threshold_blocks(self):
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=0.02)
        assert result.passed is False


class TestStopLossCooling:
    """24h wait after stop-loss exit before re-entering same expiry."""

    def test_recent_stop_loss_blocks(self, tmp_path):
        state_path = tmp_path / "behavioral_guard_state.json"
        state = {
            "stop_loss_exits": [{"expiry": "2026-03-20", "timestamp": datetime.now().isoformat()}]
        }
        with open(state_path, "w") as f:
            json.dump(state, f)

        with patch("src.safety.behavioral_guard._STATE_PATH", state_path):
            result = BehavioralGuard.evaluate("SPY", expiry="2026-03-20", spy_change_pct=0.001)
        assert result.passed is False
        assert any("Cooling" in r for r in result.rejections)

    def test_old_stop_loss_allows(self, tmp_path):
        state_path = tmp_path / "behavioral_guard_state.json"
        old_time = datetime.now() - timedelta(hours=25)
        state = {"stop_loss_exits": [{"expiry": "2026-03-20", "timestamp": old_time.isoformat()}]}
        with open(state_path, "w") as f:
            json.dump(state, f)

        with patch("src.safety.behavioral_guard._STATE_PATH", state_path):
            result = BehavioralGuard.evaluate("SPY", expiry="2026-03-20", spy_change_pct=0.001)
        assert not any("Cooling" in r for r in result.rejections)

    def test_different_expiry_allows(self, tmp_path):
        state_path = tmp_path / "behavioral_guard_state.json"
        state = {
            "stop_loss_exits": [{"expiry": "2026-03-20", "timestamp": datetime.now().isoformat()}]
        }
        with open(state_path, "w") as f:
            json.dump(state, f)

        with patch("src.safety.behavioral_guard._STATE_PATH", state_path):
            result = BehavioralGuard.evaluate("SPY", expiry="2026-03-27", spy_change_pct=0.001)
        assert not any("Cooling" in r for r in result.rejections)

    def test_record_and_prune(self, tmp_path):
        state_path = tmp_path / "behavioral_guard_state.json"
        old_time = datetime.now() - timedelta(hours=49)
        state = {"stop_loss_exits": [{"expiry": "2026-02-20", "timestamp": old_time.isoformat()}]}
        with open(state_path, "w") as f:
            json.dump(state, f)

        with patch("src.safety.behavioral_guard._STATE_PATH", state_path):
            BehavioralGuard.record_stop_loss_exit("2026-03-20")

        with open(state_path) as f:
            updated = json.load(f)

        # Old entry pruned, new entry present
        assert len(updated["stop_loss_exits"]) == 1
        assert updated["stop_loss_exits"][0]["expiry"] == "2026-03-20"


class TestBlacklist:
    """Belt+suspenders blacklist check against TargetSymbols.BLACKLIST."""

    def test_blacklisted_ticker_blocked(self):
        result = BehavioralGuard.evaluate("SOFI", spy_change_pct=0.001)
        assert result.passed is False
        assert any("Blacklisted" in r for r in result.rejections)

    def test_spy_not_blacklisted(self):
        result = BehavioralGuard.evaluate("SPY", spy_change_pct=0.001)
        assert not any("Blacklisted" in r for r in result.rejections)

    def test_blacklisted_option_symbol(self):
        """OCC option symbol for SOFI should also be blocked."""
        result = BehavioralGuard.evaluate("SOFI260206P00024000", spy_change_pct=0.001)
        assert any("Blacklisted" in r for r in result.rejections)


class TestIntegration:
    """End-to-end behavioral guard scenarios."""

    def test_clean_trade_passes_all(self):
        result = BehavioralGuard.evaluate("SPY", expiry="2026-04-17", spy_change_pct=0.005)
        assert result.passed is True
        assert len(result.checks_run) == 3
        assert len(result.rejections) == 0

    def test_multiple_rejections(self):
        """FOMO + blacklist can both trigger."""
        result = BehavioralGuard.evaluate("SOFI", spy_change_pct=0.03)
        assert result.passed is False
        assert len(result.rejections) >= 2
