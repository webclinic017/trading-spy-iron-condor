#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def section_lines(path: Path, header: str) -> list[str]:
    lines = read_text(path).splitlines()
    out: list[str] = []
    in_section = False
    for line in lines:
        s = line.rstrip()
        if s.startswith("## ") and s == f"## {header}":
            in_section = True
            continue
        if in_section and s.startswith("## "):
            break
        if in_section:
            out.append(s)
    return out


def parse_open_layer1(tasks_path: Path) -> list[str]:
    out: list[str] = []
    for line in section_lines(tasks_path, "Layer 1: Red Build/Test Failures"):
        s = line.strip()
        if s.startswith("- [ ] "):
            out.append(s[6:].strip())
    return out


def extract_prefixed(path: Path, prefix: str) -> str:
    for line in read_text(path).splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return "N/A"


def tail_lines(path: Path, n: int = 20) -> list[str]:
    lines = read_text(path).splitlines()
    return lines[-n:] if lines else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate morning status report from devloop artifacts.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--out", default="artifacts/devloop/morning_report.md", help="Output report path"
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = (repo_root / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    tasks = repo_root / "artifacts/devloop/tasks.md"
    kpi_priority = repo_root / "artifacts/devloop/kpi_priority_report.md"
    scorecard = repo_root / "artifacts/devloop/profit_readiness_scorecard.md"
    rag_status = repo_root / "artifacts/devloop/rag_status.md"
    continuous_log = repo_root / "artifacts/devloop/continuous.log"

    open_layer1 = parse_open_layer1(tasks)
    focus_metric = extract_prefixed(kpi_priority, "- Focus metric:")
    deficit = extract_prefixed(kpi_priority, "- Deficit score:")
    stall = extract_prefixed(kpi_priority, "- Stall pivot active:")
    rag_overall = extract_prefixed(rag_status, "- RAG refresh overall:")
    win_rate = extract_prefixed(scorecard, "- Win Rate:")
    run_rate = extract_prefixed(scorecard, "- Monthly run-rate estimate:")
    drawdown = extract_prefixed(scorecard, "- Max Drawdown (sync history):")

    lines: list[str] = []
    lines.append("# Morning Devloop Report")
    lines.append("")
    lines.append(f"- Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("")
    lines.append("## KPI Focus")
    lines.append(f"- Focus metric: {focus_metric}")
    lines.append(f"- Deficit: {deficit}")
    lines.append(f"- Stall pivot active: {stall}")
    lines.append("")
    lines.append("## Profit Readiness Snapshot")
    lines.append(f"- Win Rate: {win_rate}")
    lines.append(f"- Monthly run-rate estimate: {run_rate}")
    lines.append(f"- Max Drawdown: {drawdown}")
    lines.append("")
    lines.append("## RAG Snapshot")
    lines.append(f"- {rag_overall}")
    lines.append("")
    lines.append("## Layer 1 Open Tasks")
    if open_layer1:
        for item in open_layer1[:10]:
            lines.append(f"- [ ] {item}")
    else:
        lines.append("- [x] None")
    lines.append("")
    lines.append("## Last Log Lines")
    for line in tail_lines(continuous_log, n=20):
        lines.append(f"- `{line}`")
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: morning report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
