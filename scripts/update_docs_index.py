#!/usr/bin/env python3
"""
Auto-update docs/index.md with current data from data/system_state.json.

This script replaces a marker-delimited status block on the homepage:
- never relies on brittle regexes tied to specific prose
- updates date/day/equity/P&L/open positions/win-rate/last-sync
- keeps the rest of docs/index.md fully editable

Run by: .github/workflows/update-progress-dashboard.yml
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_START_DATE = date(2025, 10, 29)
TARGET_PHASE_DAYS = 90
SYSTEM_STATE_PATH = Path("data/system_state.json")
DOCS_INDEX_PATH = Path("docs/index.md")
AUTO_STATUS_START = "<!-- AUTO_STATUS_START -->"
AUTO_STATUS_END = "<!-- AUTO_STATUS_END -->"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_signed_currency(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def calculate_day_number(today: date | None = None) -> int:
    ref = today or datetime.now(timezone.utc).date()
    return max(1, (ref - PROJECT_START_DATE).days + 1)


def load_system_state() -> dict[str, Any]:
    if not SYSTEM_STATE_PATH.exists():
        return {}
    try:
        with SYSTEM_STATE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_status_metrics(state: dict[str, Any]) -> dict[str, Any]:
    paper = state.get("paper_account", {}) if isinstance(state, dict) else {}
    portfolio = state.get("portfolio", {}) if isinstance(state, dict) else {}
    positions = state.get("positions", []) if isinstance(state.get("positions"), list) else []

    equity = _as_float(paper.get("equity"), 0.0)
    if equity <= 0:
        equity = _as_float(paper.get("current_equity"), 0.0)
    if equity <= 0:
        equity = _as_float(portfolio.get("equity"), 0.0)

    daily_pl = _as_float(paper.get("daily_change"), 0.0)
    if daily_pl == 0:
        daily_pl = _as_float(paper.get("todays_pl"), 0.0)

    daily_pl_pct = _as_float(paper.get("todays_pl_pct"), 0.0)
    if daily_pl_pct == 0 and equity > 0 and (equity - daily_pl) > 0:
        daily_pl_pct = (daily_pl / (equity - daily_pl)) * 100.0

    position_legs = _as_int(paper.get("positions_count"), 0)
    if position_legs <= 0:
        position_legs = len(positions)

    if position_legs > 0 and position_legs % 4 == 0:
        condors = position_legs // 4
        noun = "iron condor" if condors == 1 else "iron condors"
        open_positions = f"{condors} {noun} ({position_legs} option legs)"
    elif position_legs > 0:
        open_positions = f"{position_legs} option legs"
    else:
        open_positions = "0"

    position_pl = 0.0
    for pos in positions:
        if not isinstance(pos, dict):
            continue
        position_pl += _as_float(pos.get("pnl", pos.get("unrealized_pl", 0.0)), 0.0)

    win_rate = paper.get("win_rate")
    win_rate_sample = _as_int(paper.get("win_rate_sample_size"), 0)
    if win_rate is None:
        win_rate_display = "N/A"
    elif win_rate_sample > 0:
        win_rate_display = f"{_as_float(win_rate):.1f}% ({win_rate_sample} trades)"
    else:
        win_rate_display = f"{_as_float(win_rate):.1f}%"

    last_sync_raw = (
        state.get("last_updated")
        or state.get("sync_health", {}).get("last_successful_sync")
        or state.get("meta", {}).get("last_updated")
    )
    parsed_sync = _parse_iso_datetime(last_sync_raw)
    if parsed_sync:
        last_sync_display = parsed_sync.strftime("%Y-%m-%d %H:%M UTC")
    else:
        last_sync_display = "Unknown"

    day_number = calculate_day_number()
    today_label = datetime.now(timezone.utc).strftime("%A, %B %d, %Y").replace(" 0", " ")
    if day_number <= TARGET_PHASE_DAYS:
        phase_line = f"Day {day_number} of {TARGET_PHASE_DAYS}-day paper trading phase."
    else:
        phase_line = (
            f"Day {day_number} since project start "
            f"(initial paper-phase target: {TARGET_PHASE_DAYS} days)."
        )

    return {
        "day_number": day_number,
        "phase_line": phase_line,
        "today_label": today_label,
        "equity": equity,
        "daily_pl": daily_pl,
        "daily_pl_pct": daily_pl_pct,
        "open_positions": open_positions,
        "position_pl": position_pl,
        "win_rate": win_rate_display,
        "last_sync": last_sync_display,
    }


def render_status_block(metrics: dict[str, Any]) -> str:
    return (
        f"{AUTO_STATUS_START}\n"
        f"## Where We Are Today ({metrics['today_label']})\n\n"
        f"{metrics['phase_line']}\n\n"
        "| What | Status |\n"
        "| --- | --- |\n"
        f"| Account Equity | ${metrics['equity']:,.2f} |\n"
        f"| Daily P/L | {_format_signed_currency(metrics['daily_pl'])} ({metrics['daily_pl_pct']:+.2f}%) |\n"
        "| Strategy | Iron Condors on SPY |\n"
        f"| Open Positions | {metrics['open_positions']} |\n"
        f"| Position P/L | {_format_signed_currency(metrics['position_pl'])} |\n"
        f"| Win Rate | {metrics['win_rate']} |\n"
        f"| Last Sync | {metrics['last_sync']} |\n\n"
        "Source of truth: [data/system_state.json](https://github.com/IgorGanapolsky/trading/blob/main/data/system_state.json)\n"
        f"{AUTO_STATUS_END}"
    )


def update_docs_index() -> bool:
    if not DOCS_INDEX_PATH.exists():
        print(f"Error: {DOCS_INDEX_PATH} not found")
        return False

    state = load_system_state()
    metrics = build_status_metrics(state)
    new_block = render_status_block(metrics)

    content = DOCS_INDEX_PATH.read_text(encoding="utf-8")
    original = content

    marker_pattern = re.compile(
        re.escape(AUTO_STATUS_START) + r".*?" + re.escape(AUTO_STATUS_END),
        re.DOTALL,
    )

    if marker_pattern.search(content):
        content = marker_pattern.sub(new_block, content, count=1)
    else:
        legacy_pattern = re.compile(
            r"## Where We Are Today \([^)]+\)\n.*?\n---\n\n## The Story So Far",
            re.DOTALL,
        )
        if legacy_pattern.search(content):
            replacement = new_block + "\n\n---\n\n## The Story So Far"
            content = legacy_pattern.sub(replacement, content, count=1)
        else:
            insertion_point = "\n---\n\n## The Story So Far"
            if insertion_point in content:
                content = content.replace(insertion_point, f"\n\n{new_block}{insertion_point}", 1)
            else:
                content = content.rstrip() + "\n\n---\n\n" + new_block + "\n"

    if content == original:
        print("No changes needed to docs/index.md")
        return True

    DOCS_INDEX_PATH.write_text(content, encoding="utf-8")
    print("Updated docs/index.md:")
    print(f"  - Day: {metrics['day_number']}")
    print(f"  - Date: {metrics['today_label']}")
    print(f"  - Equity: ${metrics['equity']:,.2f}")
    print(f"  - Daily P/L: {_format_signed_currency(metrics['daily_pl'])}")
    print(f"  - Open Positions: {metrics['open_positions']}")
    print(f"  - Last Sync: {metrics['last_sync']}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if update_docs_index() else 1)
