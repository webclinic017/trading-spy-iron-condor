import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _base_state() -> dict:
    return {
        "meta": {"version": "1.0"},
        "paper_account": {"starting_balance": 5000.0},
        "live_account": {"starting_balance": 20.0},
        "account": {},
        "performance": {"open_positions": []},
    }


def _alpaca_payload(paper_equity: float, paper_daily_change: float, live_equity: float) -> dict:
    return {
        "paper": {
            "equity": paper_equity,
            "cash": 1000.0,
            "buying_power": 1000.0,
            "positions": [],
            "positions_count": 0,
            "daily_change": paper_daily_change,
            "mode": "paper",
            "synced_at": "2026-02-23T15:00:00",
        },
        "live": {
            "equity": live_equity,
            "cash": 100.0,
            "buying_power": 100.0,
            "positions_count": 0,
            "daily_change": 0.0,
            "mode": "live",
            "synced_at": "2026-02-23T15:00:00",
        },
    }


def test_intraday_snapshot_files_created_and_latest_matches_history(tmp_path):
    state_file = tmp_path / "data" / "system_state.json"
    runtime_dir = tmp_path / "data" / "runtime"
    history_file = runtime_dir / "intraday_pnl_history.json"
    latest_file = runtime_dir / "intraday_pnl_latest.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps(_base_state()))

    with (
        patch("sync_alpaca_state.SYSTEM_STATE_FILE", state_file),
        patch("sync_alpaca_state.RUNTIME_DIR", runtime_dir),
        patch("sync_alpaca_state.INTRADAY_PNL_HISTORY_FILE", history_file),
        patch("sync_alpaca_state.INTRADAY_PNL_LATEST_FILE", latest_file),
    ):
        from sync_alpaca_state import update_system_state

        update_system_state(_alpaca_payload(101000.25, -12.34, 209.15))

    history = json.loads(history_file.read_text())
    latest = json.loads(latest_file.read_text())

    assert len(history) == 1
    assert latest == history[-1]
    assert latest["paper"]["equity"] == 101000.25
    assert latest["paper"]["daily_change"] == -12.34
    assert latest["live"]["equity"] == 209.15
    assert latest["sync_mode"] == "paper+live"


def test_intraday_snapshot_history_is_bounded(tmp_path):
    state_file = tmp_path / "data" / "system_state.json"
    runtime_dir = tmp_path / "data" / "runtime"
    history_file = runtime_dir / "intraday_pnl_history.json"
    latest_file = runtime_dir / "intraday_pnl_latest.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps(_base_state()))

    with (
        patch("sync_alpaca_state.SYSTEM_STATE_FILE", state_file),
        patch("sync_alpaca_state.RUNTIME_DIR", runtime_dir),
        patch("sync_alpaca_state.INTRADAY_PNL_HISTORY_FILE", history_file),
        patch("sync_alpaca_state.INTRADAY_PNL_LATEST_FILE", latest_file),
        patch("sync_alpaca_state.INTRADAY_HISTORY_LIMIT", 2),
    ):
        from sync_alpaca_state import update_system_state

        update_system_state(_alpaca_payload(100100.0, 1.0, 200.0))
        update_system_state(_alpaca_payload(100200.0, 2.0, 201.0))
        update_system_state(_alpaca_payload(100300.0, 3.0, 202.0))

    history = json.loads(history_file.read_text())
    assert len(history) == 2
    assert [row["paper"]["daily_change"] for row in history] == [2.0, 3.0]


def test_intraday_snapshot_persists_when_sync_skips_no_keys(tmp_path):
    state_file = tmp_path / "data" / "system_state.json"
    runtime_dir = tmp_path / "data" / "runtime"
    history_file = runtime_dir / "intraday_pnl_history.json"
    latest_file = runtime_dir / "intraday_pnl_latest.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        json.dumps(
            {
                "meta": {"version": "1.0"},
                "paper_account": {
                    "starting_balance": 5000.0,
                    "equity": 101111.11,
                    "daily_change": -5.55,
                    "positions_count": 1,
                    "synced_at": "2026-02-22T20:00:00",
                },
                "live_account": {
                    "starting_balance": 20.0,
                    "equity": 208.88,
                    "daily_change": 0.0,
                    "positions_count": 0,
                    "synced_at": "2026-02-22T20:00:00",
                },
            }
        )
    )

    with (
        patch("sync_alpaca_state.SYSTEM_STATE_FILE", state_file),
        patch("sync_alpaca_state.RUNTIME_DIR", runtime_dir),
        patch("sync_alpaca_state.INTRADAY_PNL_HISTORY_FILE", history_file),
        patch("sync_alpaca_state.INTRADAY_PNL_LATEST_FILE", latest_file),
    ):
        from sync_alpaca_state import update_system_state

        update_system_state(None)

    latest = json.loads(latest_file.read_text())
    assert latest["sync_mode"] == "skipped_no_keys"
    assert latest["paper"]["equity"] == 101111.11
    assert latest["paper"]["daily_change"] == -5.55
    assert latest["live"]["equity"] == 208.88
