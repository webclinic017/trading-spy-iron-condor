#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

TS_RE = re.compile(r"^\[(?P<ts>[^]]+)\]\s+(?P<msg>.*)$")
ANALYZE_START_RE = re.compile(r"cycle=(\d+)\s+profile=([a-zA-Z0-9_-]+)\s+analyze start")
ANALYZE_DONE_RE = re.compile(r"cycle=(\d+)\s+profile=([a-zA-Z0-9_-]+)\s+analyze done")
TARS_START_RE = re.compile(r"cycle=(\d+)\s+tars full start")
TARS_DONE_RE = re.compile(r"cycle=(\d+)\s+tars full done")
RAG_START_RE = re.compile(r"cycle=(\d+)\s+rag refresh start")
RAG_DONE_RE = re.compile(r"cycle=(\d+)\s+rag refresh done")
OPEN_TASK_RE = re.compile(r"^- \[ \] (.+)$")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def format_elapsed(delta_seconds: float) -> str:
    seconds = int(max(delta_seconds, 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def parse_open_tasks(task_file: Path) -> list[str]:
    tasks: list[str] = []
    for line in read_text(task_file).splitlines():
        match = OPEN_TASK_RE.match(line.strip())
        if match:
            tasks.append(match.group(1).strip())
    return tasks


def parse_phase_times(log_path: Path) -> dict[str, str]:
    lines = read_text(log_path).splitlines()

    analyze_start: tuple[datetime, str] | None = None
    analyze_done: tuple[datetime, str] | None = None
    tars_start: tuple[datetime, str] | None = None
    tars_done: tuple[datetime, str] | None = None
    rag_start: tuple[datetime, str] | None = None
    rag_done: tuple[datetime, str] | None = None

    for line in lines:
        m = TS_RE.match(line)
        if not m:
            continue
        ts = parse_ts(m.group("ts"))
        msg = m.group("msg")
        if ts is None:
            continue

        a_start = ANALYZE_START_RE.search(msg)
        if a_start:
            analyze_start = (ts, f"cycle={a_start.group(1)} profile={a_start.group(2)}")
            analyze_done = None
            continue
        a_done = ANALYZE_DONE_RE.search(msg)
        if (
            a_done
            and analyze_start
            and f"cycle={a_done.group(1)} profile={a_done.group(2)}" in analyze_start[1]
        ):
            analyze_done = (ts, analyze_start[1])
            continue

        t_start = TARS_START_RE.search(msg)
        if t_start:
            tars_start = (ts, f"cycle={t_start.group(1)}")
            tars_done = None
            continue
        t_done = TARS_DONE_RE.search(msg)
        if t_done and tars_start and f"cycle={t_done.group(1)}" in tars_start[1]:
            tars_done = (ts, tars_start[1])
            continue

        r_start = RAG_START_RE.search(msg)
        if r_start:
            rag_start = (ts, f"cycle={r_start.group(1)}")
            rag_done = None
            continue
        r_done = RAG_DONE_RE.search(msg)
        if r_done and rag_start and f"cycle={r_done.group(1)}" in rag_start[1]:
            rag_done = (ts, rag_start[1])
            continue

    out: dict[str, str] = {}
    if analyze_start:
        if analyze_done:
            out["analyze_last"] = (
                f"{analyze_start[1]} duration={format_elapsed((analyze_done[0] - analyze_start[0]).total_seconds())}"
            )
        else:
            out["analyze_current"] = (
                f"{analyze_start[1]} elapsed={format_elapsed((now_utc() - analyze_start[0]).total_seconds())}"
            )
    if tars_start:
        if tars_done:
            out["tars_last"] = (
                f"{tars_start[1]} duration={format_elapsed((tars_done[0] - tars_start[0]).total_seconds())}"
            )
        else:
            out["tars_current"] = (
                f"{tars_start[1]} elapsed={format_elapsed((now_utc() - tars_start[0]).total_seconds())}"
            )
    if rag_start:
        if rag_done:
            out["rag_last"] = (
                f"{rag_start[1]} duration={format_elapsed((rag_done[0] - rag_start[0]).total_seconds())}"
            )
        else:
            out["rag_current"] = (
                f"{rag_start[1]} elapsed={format_elapsed((now_utc() - rag_start[0]).total_seconds())}"
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate active task runtime report for the live loop."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--manual", default="manual_layer1_tasks.md", help="Manual layer-1 task file"
    )
    parser.add_argument(
        "--state", default="artifacts/devloop/task_runtime_state.json", help="State file path"
    )
    parser.add_argument(
        "--log", default="artifacts/devloop/continuous.log", help="Continuous loop log path"
    )
    parser.add_argument(
        "--out", default="artifacts/devloop/task_runtime_report.md", help="Output report markdown"
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    manual = root / args.manual
    state_path = root / args.state
    log_path = root / args.log
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    now = now_utc()
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    open_tasks = parse_open_tasks(manual)

    state = read_json(state_path)
    first_seen = (
        state.get("first_seen", {}) if isinstance(state.get("first_seen", {}), dict) else {}
    )

    new_tasks: list[str] = []
    for task in open_tasks:
        if task not in first_seen:
            first_seen[task] = now_s
            new_tasks.append(task)

    # Drop completed tasks from active state.
    open_set = set(open_tasks)
    first_seen = {k: v for k, v in first_seen.items() if k in open_set}

    write_json(state_path, {"first_seen": first_seen, "last_generated_utc": now_s})

    phases = parse_phase_times(log_path)

    lines: list[str] = []
    lines.append("# Live Task Runtime Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{now_s}`")
    lines.append(f"- Open Layer-1 tasks: `{len(open_tasks)}`")
    lines.append("")
    lines.append("## Active Tasks (with elapsed time)")
    if open_tasks:
        for task in open_tasks:
            first = parse_ts(first_seen.get(task, now_s)) or now
            elapsed = format_elapsed((now - first).total_seconds())
            badge = "NEW" if task in new_tasks else "ACTIVE"
            lines.append(f"- `{badge}` {task} (elapsed: {elapsed})")
    else:
        lines.append("- No open Layer-1 tasks.")
    lines.append("")
    lines.append("## Current Task In Progress")
    if open_tasks:
        current_task = open_tasks[0]
        current_start_raw = first_seen.get(current_task, now_s)
        current_start = parse_ts(current_start_raw) or now
        current_elapsed = format_elapsed((now - current_start).total_seconds())
        lines.append(f"- Task: {current_task}")
        lines.append(f"- Started (UTC): `{current_start.strftime('%Y-%m-%dT%H:%M:%SZ')}`")
        lines.append(f"- Elapsed: `{current_elapsed}`")
    else:
        lines.append("- No active task.")
    lines.append("")
    lines.append("## Runtime Phases")
    if phases:
        if "analyze_current" in phases:
            lines.append(f"- Analyze in progress: {phases['analyze_current']}")
        if "tars_current" in phases:
            lines.append(f"- TARS in progress: {phases['tars_current']}")
        if "rag_current" in phases:
            lines.append(f"- RAG in progress: {phases['rag_current']}")
        if "analyze_last" in phases:
            lines.append(f"- Last analyze: {phases['analyze_last']}")
        if "tars_last" in phases:
            lines.append(f"- Last TARS: {phases['tars_last']}")
        if "rag_last" in phases:
            lines.append(f"- Last RAG: {phases['rag_last']}")
    else:
        lines.append("- No phase timing detected yet.")
    lines.append("")
    lines.append("## Newly Added Tasks This Run")
    if new_tasks:
        for item in new_tasks:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Sources")
    lines.append(f"- `{manual.relative_to(root)}`")
    lines.append(f"- `{log_path.relative_to(root)}`")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: task runtime report -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
