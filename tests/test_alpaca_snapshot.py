"""Tests for the Alpaca portfolio snapshot generator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def snapshot_dir(tmp_path):
    """Create a temporary snapshot directory."""
    d = tmp_path / "docs" / "assets" / "snapshots"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def mock_paper_data():
    return {
        "account_type": "paper",
        "equity": 101441.56,
        "cash": 85000.0,
        "buying_power": 170000.0,
        "starting_capital": 100000.0,
        "position_count": 4,
        "positions": [
            {"symbol": "SPY260313P00650000", "qty": -2.0, "market_value": -100.0, "unrealized_pl": 50.0},
        ],
    }


@pytest.fixture
def mock_brokerage_data():
    return {
        "account_type": "brokerage",
        "equity": 167.48,
        "cash": 167.48,
        "buying_power": 334.96,
        "starting_capital": 5000.0,
        "position_count": 0,
        "positions": [],
    }


class TestGenerateChart:
    def test_generates_png(self, tmp_path, mock_paper_data):
        """Test chart generation produces a PNG file."""
        from scripts.generate_alpaca_snapshot import generate_chart

        output = tmp_path / "test_chart.png"
        result = generate_chart(mock_paper_data, output)
        assert result is True
        assert output.exists()
        assert output.stat().st_size > 0

    def test_positive_change_color(self, tmp_path, mock_paper_data):
        """Test chart with positive P/L."""
        from scripts.generate_alpaca_snapshot import generate_chart

        output = tmp_path / "positive.png"
        result = generate_chart(mock_paper_data, output)
        assert result is True

    def test_negative_change_color(self, tmp_path, mock_brokerage_data):
        """Test chart with negative P/L."""
        from scripts.generate_alpaca_snapshot import generate_chart

        output = tmp_path / "negative.png"
        result = generate_chart(mock_brokerage_data, output)
        assert result is True

    def test_creates_parent_dirs(self, tmp_path, mock_paper_data):
        """Test chart creates parent directories."""
        from scripts.generate_alpaca_snapshot import generate_chart

        output = tmp_path / "nested" / "dir" / "chart.png"
        result = generate_chart(mock_paper_data, output)
        assert result is True
        assert output.exists()


class TestFetchAccounts:
    @patch("src.utils.alpaca_client.get_alpaca_credentials", return_value=(None, None))
    def test_paper_no_credentials(self, mock_creds):
        """Test paper account returns None when no credentials."""
        from scripts.generate_alpaca_snapshot import fetch_paper_account

        result = fetch_paper_account()
        assert result is None

    @patch("src.utils.alpaca_client.get_brokerage_credentials", return_value=(None, None))
    def test_brokerage_no_credentials(self, mock_creds):
        """Test brokerage account returns None when no credentials."""
        from scripts.generate_alpaca_snapshot import fetch_brokerage_account

        result = fetch_brokerage_account()
        assert result is None


class TestConstants:
    def test_chart_colors_are_hex(self):
        """Test chart theme colors are valid hex."""
        from scripts.generate_alpaca_snapshot import (
            CHART_ACCENT,
            CHART_BG,
            CHART_LINE,
            CHART_MUTED,
            CHART_PANEL,
            CHART_PASS,
            CHART_TEXT,
        )

        for color in [CHART_BG, CHART_PANEL, CHART_TEXT, CHART_MUTED, CHART_ACCENT, CHART_PASS, CHART_LINE]:
            assert color.startswith("#"), f"{color} is not a hex color"
            assert len(color) == 7, f"{color} is not a valid 6-digit hex color"

    def test_starting_capitals(self):
        """Test starting capital values are set correctly."""
        from scripts.generate_alpaca_snapshot import BROKERAGE_STARTING, PAPER_STARTING

        assert PAPER_STARTING == 100_000.0
        assert BROKERAGE_STARTING == 5_000.0
