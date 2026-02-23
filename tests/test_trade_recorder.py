"""Tests for src/utils/trade_recorder.py."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch


from src.utils.trade_recorder import get_daily_trades, get_trade_count, record_trade_result


# --- record_trade_result ---


def test_record_trade_creates_file(tmp_path):
    path = record_trade_result(
        symbol="SPY",
        strategy="iron_condors",
        result={"status": "FILLED", "order_id": "abc123"},
        data_dir=str(tmp_path),
    )
    assert path.exists()
    trades = json.loads(path.read_text())
    assert len(trades) == 1
    assert trades[0]["symbol"] == "SPY"
    assert trades[0]["strategy"] == "iron_condors"
    assert trades[0]["result"]["status"] == "FILLED"
    assert "timestamp" in trades[0]


def test_record_trade_appends_to_existing(tmp_path):
    record_trade_result(
        symbol="SPY", strategy="ic", result={"id": "1"}, data_dir=str(tmp_path)
    )
    record_trade_result(
        symbol="SPY", strategy="ic", result={"id": "2"}, data_dir=str(tmp_path)
    )
    # Both should be in the same daily file
    trades = get_daily_trades("ic", data_dir=str(tmp_path))
    assert len(trades) == 2
    assert trades[0]["result"]["id"] == "1"
    assert trades[1]["result"]["id"] == "2"


def test_record_trade_extra_fields(tmp_path):
    path = record_trade_result(
        symbol="SPY",
        strategy="ic",
        result={"status": "FILLED"},
        data_dir=str(tmp_path),
        extra_fields={"width": 10, "delta": 0.15},
    )
    trades = json.loads(path.read_text())
    assert trades[0]["width"] == 10
    assert trades[0]["delta"] == 0.15


def test_record_trade_no_extra_fields(tmp_path):
    path = record_trade_result(
        symbol="SPY",
        strategy="ic",
        result={"status": "FILLED"},
        data_dir=str(tmp_path),
    )
    trades = json.loads(path.read_text())
    assert "width" not in trades[0]


def test_record_trade_creates_nested_data_dir(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    path = record_trade_result(
        symbol="SPY", strategy="ic", result={}, data_dir=str(nested)
    )
    assert path.exists()
    assert nested.exists()


def test_record_trade_returns_path_with_date_and_strategy(tmp_path):
    with patch("src.utils.trade_recorder.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 15, 10, 30, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        path = record_trade_result(
            symbol="SPY", strategy="options_trades", result={}, data_dir=str(tmp_path)
        )
    assert path.name == "options_trades_20260315.json"


def test_record_trade_handles_corrupt_json(tmp_path):
    """If existing file has invalid JSON, start fresh instead of crashing."""
    date_str = datetime.now().strftime("%Y%m%d")
    bad_file = tmp_path / f"ic_{date_str}.json"
    bad_file.write_text("{not valid json!!")

    path = record_trade_result(
        symbol="SPY", strategy="ic", result={"ok": True}, data_dir=str(tmp_path)
    )
    trades = json.loads(path.read_text())
    assert len(trades) == 1
    assert trades[0]["result"]["ok"] is True


def test_record_trade_handles_empty_file(tmp_path):
    """Empty file should not crash -- treat as no existing trades."""
    date_str = datetime.now().strftime("%Y%m%d")
    empty_file = tmp_path / f"ic_{date_str}.json"
    empty_file.write_text("")

    path = record_trade_result(
        symbol="SPY", strategy="ic", result={"x": 1}, data_dir=str(tmp_path)
    )
    trades = json.loads(path.read_text())
    assert len(trades) == 1


# --- get_daily_trades ---


def test_get_daily_trades_returns_list(tmp_path):
    record_trade_result(
        symbol="SPY", strategy="ic", result={"a": 1}, data_dir=str(tmp_path)
    )
    trades = get_daily_trades("ic", data_dir=str(tmp_path))
    assert isinstance(trades, list)
    assert len(trades) == 1


def test_get_daily_trades_nonexistent_file(tmp_path):
    trades = get_daily_trades("nonexistent_strategy", data_dir=str(tmp_path))
    assert trades == []


def test_get_daily_trades_empty_file(tmp_path):
    date_str = datetime.now().strftime("%Y%m%d")
    (tmp_path / f"ic_{date_str}.json").write_text("  ")
    trades = get_daily_trades("ic", data_dir=str(tmp_path))
    assert trades == []


def test_get_daily_trades_corrupt_json(tmp_path):
    date_str = datetime.now().strftime("%Y%m%d")
    (tmp_path / f"ic_{date_str}.json").write_text("NOT JSON")
    trades = get_daily_trades("ic", data_dir=str(tmp_path))
    assert trades == []


def test_get_daily_trades_specific_date(tmp_path):
    target_date = datetime(2026, 1, 5)
    date_str = target_date.strftime("%Y%m%d")
    trade_file = tmp_path / f"ic_{date_str}.json"
    trade_file.write_text(json.dumps([{"symbol": "SPY", "result": {"ok": True}}]))

    trades = get_daily_trades("ic", data_dir=str(tmp_path), date=target_date)
    assert len(trades) == 1
    assert trades[0]["symbol"] == "SPY"


def test_get_daily_trades_wrong_date_returns_empty(tmp_path):
    """Trades recorded today should not appear when querying a different date."""
    record_trade_result(
        symbol="SPY", strategy="ic", result={}, data_dir=str(tmp_path)
    )
    other_date = datetime(2020, 1, 1)
    trades = get_daily_trades("ic", data_dir=str(tmp_path), date=other_date)
    assert trades == []


# --- get_trade_count ---


def test_get_trade_count_zero_when_no_file(tmp_path):
    assert get_trade_count("ic", data_dir=str(tmp_path)) == 0


def test_get_trade_count_matches_recorded(tmp_path):
    for i in range(3):
        record_trade_result(
            symbol="SPY", strategy="ic", result={"i": i}, data_dir=str(tmp_path)
        )
    assert get_trade_count("ic", data_dir=str(tmp_path)) == 3


def test_get_trade_count_specific_date(tmp_path):
    target = datetime(2026, 6, 1)
    date_str = target.strftime("%Y%m%d")
    trade_file = tmp_path / f"ic_{date_str}.json"
    trade_file.write_text(json.dumps([{"a": 1}, {"b": 2}]))
    assert get_trade_count("ic", data_dir=str(tmp_path), date=target) == 2
