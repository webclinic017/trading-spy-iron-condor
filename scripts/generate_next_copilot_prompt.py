#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

CHECKBOX_RE = re.compile(r"^- \[( |x)\] (.+)$")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def unchecked_items(path: Path, max_items: int = 8) -> list[str]:
    items: list[str] = []
    in_layer1 = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("## Layer 1:"):
            in_layer1 = True
            continue
        if in_layer1 and stripped.startswith("## "):
            break
        if not in_layer1:
            continue
        m = CHECKBOX_RE.match(stripped)
        if not m:
            continue
        if m.group(1) == " ":
            items.append(m.group(2).strip())
        if len(items) >= max_items:
            break
    return items


def first_open_manual(path: Path) -> str | None:
    for line in read_text(path).splitlines():
        m = CHECKBOX_RE.match(line.strip())
        if not m:
            continue
        if m.group(1) == " ":
            return m.group(2).strip()
    return None


def parse_gate(path: Path) -> tuple[str, str]:
    lint = "UNKNOWN"
    tests = "UNKNOWN"
    for line in read_text(path).splitlines():
        if line.startswith("ruff_exit="):
            lint = "PASS" if line.split("=", 1)[1].strip() == "0" else "FAIL"
        if line.startswith("pytest_exit="):
            tests = "PASS" if line.split("=", 1)[1].strip() == "0" else "FAIL"
    return lint, tests


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate next Copilot prompt from devloop artifacts."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--out", default="artifacts/devloop/next_copilot_prompt.md", help="Output path"
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    tasks_path = repo_root / "artifacts/devloop/tasks.md"
    status_path = repo_root / "artifacts/devloop/status.txt"
    manual_path = (
        repo_root / "manual_layer1_tasks.md"
        if (repo_root / "manual_layer1_tasks.md").exists()
        else repo_root / "config/manual_layer1_tasks.md"
    )

    layer1 = unchecked_items(tasks_path)
    manual_open = first_open_manual(manual_path)
    lint, tests = parse_gate(status_path)

    target = layer1[0] if layer1 else (manual_open or "No open Layer 1 item found.")

    lines: list[str] = []
    lines.append("# Next Copilot Prompt")
    lines.append("")
    lines.append("Copy/paste this into Copilot Chat (Agent mode):")
    lines.append("")
    lines.append("```text")
    lines.append("Read `.github/copilot-instructions.md` and `artifacts/devloop/tasks.md`.")
    lines.append("Pick exactly one unchecked Layer 1 item and do a minimal fix.")
    lines.append("Run `./scripts/layered_tdd_loop.sh analyze` after the change.")
    lines.append("Update only necessary files and keep diffs surgical.")
    lines.append(
        "If Layer 1 is empty and checks are green, pick one open item from `manual_layer1_tasks.md`."
    )
    lines.append(f"Target item: {target}")
    lines.append(
        "Then report: files changed, command outputs summary, and which checkbox is now complete."
    )
    lines.append("```")
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Gate status: lint={lint}, tests={tests}")
    lines.append(f"- Open Layer 1 items surfaced: {len(layer1)}")
    lines.append(f"- Manual backlog source: `{manual_path.relative_to(repo_root)}`")
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: generated -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
