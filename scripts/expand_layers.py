#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHECKBOX_RE = re.compile(r"^- \[( |x)\] (.+)$")
L2_FILE_RE = re.compile(r"^- `([^`]+)` \((\d+) signal\(s\)\)$")
METRIC_RE = re.compile(r"^- ([^:]+): .+\[([A-Z]+)\]")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def section_lines(path: Path, header: str) -> list[str]:
    lines = read_text(path).splitlines()
    out: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("## ") and stripped == f"## {header}":
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section:
            out.append(stripped)
    return out


def open_layer1_items(tasks_path: Path) -> list[str]:
    out: list[str] = []
    for line in section_lines(tasks_path, "Layer 1: Red Build/Test Failures"):
        m = CHECKBOX_RE.match(line.strip())
        if not m:
            continue
        if m.group(1) == " ":
            out.append(m.group(2).strip())
    return out


def parse_layer2(tasks_path: Path) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for line in section_lines(tasks_path, "Layer 2: High-Impact Files"):
        m = L2_FILE_RE.match(line.strip())
        if not m:
            continue
        out.append((m.group(1), int(m.group(2))))
    return out


def parse_layer3(tasks_path: Path) -> list[str]:
    out: list[str] = []
    for line in section_lines(tasks_path, "Layer 3: Deferred Cleanup"):
        stripped = line.strip()
        if stripped.startswith("- ") and stripped != "- None":
            out.append(stripped[2:].strip())
    return out


def parse_warn_metrics(scorecard_path: Path) -> list[str]:
    warns: list[str] = []
    for line in section_lines(scorecard_path, "Metrics"):
        m = METRIC_RE.match(line.strip())
        if not m:
            continue
        if m.group(2) in {"WARN", "UNKNOWN"}:
            warns.append(m.group(1).strip())
    for line in section_lines(scorecard_path, "7-Day Delta"):
        m = METRIC_RE.match(line.strip())
        if not m:
            continue
        if m.group(2) in {"WARN", "UNKNOWN"}:
            warns.append(m.group(1).strip())
    return warns


def parse_manual_tasks(path: Path) -> set[str]:
    tasks: set[str] = set()
    for line in read_text(path).splitlines():
        m = CHECKBOX_RE.match(line.strip())
        if not m:
            continue
        tasks.add(m.group(2).strip())
    return tasks


def load_priority_tasks(path: Path) -> tuple[list[str], list[str], str]:
    if not path.exists():
        return [], [], "none"
    try:
        payload = json.loads(read_text(path))
    except Exception:
        return [], [], "invalid"
    recommended = [str(x).strip() for x in payload.get("recommended_tasks", []) if str(x).strip()]
    pivot = [str(x).strip() for x in payload.get("pivot_tasks", []) if str(x).strip()]
    focus_metric = str(payload.get("focus_metric", "none"))
    return recommended, pivot, focus_metric


def append_manual_tasks(path: Path, new_tasks: list[str]) -> None:
    if not path.exists():
        path.write_text("# Manual Layer 1 Tasks\n\n", encoding="utf-8")
    lines = read_text(path).splitlines()
    if lines and lines[-1].strip():
        lines.append("")
    for task in new_tasks:
        lines.append(f"- [ ] {task}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kpi_candidates(warn_metrics: list[str]) -> list[str]:
    map_by_metric = {
        "Win Rate": "Improve win rate with stricter entry filters and add a validation report proving >=55% over the latest sample window.",
        "Execution Quality (valid trade records)": "Raise execution quality by enforcing trade record integrity checks and tests to maintain >=95% valid records.",
        "Gateway Latency": "Reduce gateway latency by adding timeout/fallback tuning and capture p95 latency evidence under target.",
        "Gateway Cost (smoke call)": "Reduce gateway call cost by optimizing prompt/token usage and add a cost regression check.",
        "Equity delta": "Improve 7-day equity delta by adding one measurable strategy change and a before/after artifact.",
        "Monthly run-rate estimate": "Increase monthly run-rate with a promotion gate tied to run-rate threshold and backtest proof artifact.",
    }
    out: list[str] = []
    for metric in warn_metrics:
        for key, task in map_by_metric.items():
            if metric.startswith(key):
                out.append(task)
                break
    return out


def file_candidates(layer2_files: list[tuple[str, int]]) -> list[str]:
    out: list[str] = []
    for file_path, signals in layer2_files[:3]:
        out.append(
            f"Harden `{file_path}` with focused tests/guards to remove repeated failure signals ({signals})."
        )
    return out


def cleanup_candidates(layer3_items: list[str]) -> list[str]:
    out: list[str] = []
    for item in layer3_items[:3]:
        out.append(f"Resolve deferred cleanup item with test coverage: {item}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Expand dev loop layers with KPI-gated promotions."
    )
    parser.add_argument(
        "--tasks", default="artifacts/devloop/tasks.md", help="Layered tasks markdown"
    )
    parser.add_argument(
        "--scorecard",
        default="artifacts/devloop/profit_readiness_scorecard.md",
        help="Profit readiness scorecard markdown",
    )
    parser.add_argument(
        "--manual-file",
        default="manual_layer1_tasks.md",
        help="Persistent manual layer1 tasks file",
    )
    parser.add_argument(
        "--mirror-manual-file",
        default="config/manual_layer1_tasks.md",
        help="Optional mirrored manual tasks file",
    )
    parser.add_argument(
        "--out",
        default="artifacts/devloop/layer_expansion_report.md",
        help="Expansion report markdown",
    )
    parser.add_argument("--promote-max", type=int, default=3, help="Max promoted tasks per cycle")
    parser.add_argument(
        "--priority-json",
        default="artifacts/devloop/kpi_priority.json",
        help="Priority JSON generated by generate_kpi_priority.py",
    )
    args = parser.parse_args()

    tasks_path = Path(args.tasks)
    scorecard_path = Path(args.scorecard)
    manual_file = Path(args.manual_file)
    mirror_manual_file = Path(args.mirror_manual_file)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    priority_json = Path(args.priority_json)

    open_l1 = open_layer1_items(tasks_path)
    layer2 = parse_layer2(tasks_path)
    layer3 = parse_layer3(tasks_path)
    warns = parse_warn_metrics(scorecard_path)
    priority_recommended, priority_pivot, focus_metric = load_priority_tasks(priority_json)

    candidates: list[str] = []
    candidates.extend(priority_recommended)
    candidates.extend(priority_pivot)
    candidates.extend(kpi_candidates(warns))
    candidates.extend(file_candidates(layer2))
    candidates.extend(cleanup_candidates(layer3))

    existing_manual = parse_manual_tasks(manual_file)
    unique_candidates: list[str] = []
    for task in candidates:
        if task not in existing_manual and task not in unique_candidates:
            unique_candidates.append(task)

    promoted: list[str] = []
    reason = "Layer 1 has open items; no promotions this cycle."
    if not open_l1:
        promoted = unique_candidates[: max(0, args.promote_max)]
        if promoted:
            append_manual_tasks(manual_file, promoted)
            if mirror_manual_file != manual_file:
                mirror_manual_file.parent.mkdir(parents=True, exist_ok=True)
                mirror_manual_file.write_text(read_text(manual_file), encoding="utf-8")
            reason = f"Promoted {len(promoted)} candidate(s) into manual Layer 1."
        else:
            reason = "Layer 1 empty, but no new KPI-gated candidates found."

    lines: list[str] = []
    lines.append("# Layer Expansion Report")
    lines.append("")
    lines.append("## Decision")
    lines.append(f"- {reason}")
    lines.append(f"- Open Layer 1 count: {len(open_l1)}")
    lines.append(f"- Candidate pool size: {len(unique_candidates)}")
    lines.append(f"- Promoted this cycle: {len(promoted)}")
    lines.append(f"- Focus metric: {focus_metric}")
    lines.append("")
    lines.append("## KPI Signals")
    if warns:
        for metric in warns:
            lines.append(f"- {metric}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Candidates")
    if unique_candidates:
        for task in unique_candidates[:10]:
            lines.append(f"- {task}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Promoted Tasks")
    if promoted:
        for task in promoted:
            lines.append(f"- [ ] {task}")
    else:
        lines.append("- [x] None")
    lines.append("")
    lines.append("## Stop Conditions")
    lines.append(
        "- Stop adding layers when no WARN/UNKNOWN KPI remains and no new candidates are generated."
    )
    lines.append("- Otherwise continue cycle-by-cycle with max promotions per run.")
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: layer expansion report -> {out}")
    print(f"promoted_count={len(promoted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
