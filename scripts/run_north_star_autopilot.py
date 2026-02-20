#!/usr/bin/env python3
"""Run North Star autopilot end-to-end and persist machine-readable artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_north_star_blocker_report import compute_report
from src.safety.north_star_autopilot import (
    apply_snapshot_to_state,
    build_autopilot_snapshot,
    render_autopilot_markdown,
    write_gate_overrides,
)
from src.safety.north_star_operating_plan import apply_operating_plan_to_state


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_state(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_history(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run North Star autopilot.")
    parser.add_argument("--state", default="data/system_state.json")
    parser.add_argument("--trades", default="data/trades.json")
    parser.add_argument("--history", default="data/north_star_weekly_history.json")
    parser.add_argument("--halt-file", default="data/TRADING_HALTED")
    parser.add_argument(
        "--json-out",
        default="artifacts/devloop/north_star_autopilot_report.json",
    )
    parser.add_argument(
        "--markdown-out",
        default="artifacts/devloop/north_star_autopilot_report.md",
    )
    parser.add_argument("--sync-state", action="store_true")
    parser.add_argument("--write-overrides", action="store_true")
    parser.add_argument("--fail-on-critical", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    state_path = Path(args.state)
    trades_path = Path(args.trades)
    history_path = Path(args.history)
    halt_file = Path(args.halt_file)

    state = _load_state(state_path)
    if not state:
        print(f"error: state file missing or invalid -> {state_path}", file=sys.stderr)
        return 1

    # Always recompute operating-plan fields first so autopilot runs on current evidence.
    apply_operating_plan_to_state(
        state,
        trades_path=trades_path,
        weekly_history_path=history_path,
    )

    now_utc = datetime.now(timezone.utc)
    blocker_report = compute_report(
        state=state,
        weekly_history=_load_history(history_path),
        halt_exists=halt_file.exists(),
        now_utc=now_utc,
    )
    snapshot = build_autopilot_snapshot(
        state=state,
        blocker_report=blocker_report,
        now_utc=now_utc,
        halt_exists=halt_file.exists(),
    )
    apply_snapshot_to_state(state, snapshot)

    override_result: dict[str, Any] = {"changed": False}
    if args.write_overrides:
        override_result = write_gate_overrides(
            data_dir=state_path.parent,
            snapshot=snapshot,
            now_utc=now_utc,
        )
        # If a liquidity-floor override changed, immediately recompute weekly gate
        # and refresh autopilot snapshot in the same run.
        if bool(override_result.get("changed")):
            apply_operating_plan_to_state(
                state,
                trades_path=trades_path,
                weekly_history_path=history_path,
            )
            now_utc = datetime.now(timezone.utc)
            blocker_report = compute_report(
                state=state,
                weekly_history=_load_history(history_path),
                halt_exists=halt_file.exists(),
                now_utc=now_utc,
            )
            snapshot = build_autopilot_snapshot(
                state=state,
                blocker_report=blocker_report,
                now_utc=now_utc,
                halt_exists=halt_file.exists(),
            )
            apply_snapshot_to_state(state, snapshot)
            override_result = write_gate_overrides(
                data_dir=state_path.parent,
                snapshot=snapshot,
                now_utc=now_utc,
            )

    snapshot["override_write"] = override_result

    if args.sync_state:
        _write_json(state_path, state)
    if args.json_out:
        _write_json(Path(args.json_out), snapshot)
    if args.markdown_out:
        _write_text(Path(args.markdown_out), render_autopilot_markdown(snapshot))

    print(json.dumps(snapshot))

    if args.fail_on_critical and snapshot.get("hard_gate_monitor", {}).get("status") == "critical":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
