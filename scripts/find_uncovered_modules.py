#!/usr/bin/env python3
"""Find Python modules in src/ that lack corresponding test files in tests/.

Scans all .py files in src/ (excluding __init__.py and __pycache__),
checks for a matching test_<module_name>.py in tests/ (including subdirectories),
and outputs a JSON report to data/coverage_gaps.json.

Usage:
    python scripts/find_uncovered_modules.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class UncoveredModule(TypedDict):
    module_path: str
    module_name: str
    priority: str


class CoverageReport(TypedDict):
    total_modules: int
    covered_modules: int
    uncovered_modules: list[UncoveredModule]
    coverage_percentage: float


# ---------------------------------------------------------------------------
# Priority mapping
# ---------------------------------------------------------------------------

HIGH_PRIORITY_DIRS: set[str] = {"agents", "core", "safety", "execution", "risk"}
MEDIUM_PRIORITY_DIRS: set[str] = {"analytics", "ml", "brokers"}


def _priority_for(module_path: Path) -> str:
    """Determine priority based on the top-level directory under src/."""
    parts = module_path.parts
    # module_path is relative to PROJECT_ROOT, e.g. src/safety/mandatory_trade_gate.py
    # parts[0] == "src", parts[1] == top-level package
    if len(parts) >= 2:
        top_dir = parts[1]
        if top_dir in HIGH_PRIORITY_DIRS:
            return "HIGH"
        if top_dir in MEDIUM_PRIORITY_DIRS:
            return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _collect_source_modules(src_dir: Path) -> list[Path]:
    """Return sorted list of .py files under src/, excluding __init__.py."""
    modules: list[Path] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if "__pycache__" in py_file.parts:
            continue
        modules.append(py_file)
    return modules


def _collect_test_names(tests_dir: Path) -> set[str]:
    """Return a set of test file stems (e.g. 'test_config') found anywhere under tests/."""
    names: set[str] = set()
    for py_file in tests_dir.rglob("test_*.py"):
        if "__pycache__" in py_file.parts:
            continue
        names.add(py_file.stem)
    return names


def _expected_test_name(module_path: Path) -> str:
    """Map a source module path to its expected test file stem.

    src/safety/mandatory_trade_gate.py  -> test_mandatory_trade_gate
    src/core/config.py                  -> test_config
    src/orchestration/harness/rlm_orchestrator.py -> test_rlm_orchestrator
    """
    return f"test_{module_path.stem}"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def build_report(project_root: Path) -> CoverageReport:
    """Scan src/ and tests/ to build the coverage-gap report."""
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"

    source_modules = _collect_source_modules(src_dir)
    test_names = _collect_test_names(tests_dir)

    uncovered: list[UncoveredModule] = []

    for module_path in source_modules:
        rel_path = module_path.relative_to(project_root)
        expected = _expected_test_name(module_path)
        if expected not in test_names:
            uncovered.append(
                UncoveredModule(
                    module_path=str(rel_path),
                    module_name=module_path.stem,
                    priority=_priority_for(rel_path),
                )
            )

    total = len(source_modules)
    covered = total - len(uncovered)
    pct = (covered / total * 100) if total > 0 else 0.0

    # Sort uncovered: HIGH first, then MEDIUM, then LOW; alphabetical within group
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    uncovered.sort(key=lambda m: (priority_order.get(m["priority"], 9), m["module_path"]))

    return CoverageReport(
        total_modules=total,
        covered_modules=covered,
        uncovered_modules=uncovered,
        coverage_percentage=round(pct, 1),
    )


def print_summary(report: CoverageReport) -> None:
    """Print a human-readable summary to stdout."""
    total = report["total_modules"]
    covered = report["covered_modules"]
    pct = report["coverage_percentage"]
    uncovered = report["uncovered_modules"]

    print("Test Coverage Gap Report")
    print("========================")
    print(f"Total source modules:   {total}")
    print(f"Covered (have tests):   {covered}")
    print(f"Uncovered (no tests):   {len(uncovered)}")
    print(f"Coverage percentage:    {pct}%")
    print()

    if not uncovered:
        print("All modules have corresponding test files.")
        return

    # Group by priority
    for priority in ("HIGH", "MEDIUM", "LOW"):
        group = [m for m in uncovered if m["priority"] == priority]
        if not group:
            continue
        print(f"--- {priority} priority ({len(group)}) ---")
        for mod in group:
            print(f"  {mod['module_path']}")
        print()


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    report = build_report(project_root)

    # Write JSON report
    output_path = project_root / "data" / "coverage_gaps.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print_summary(report)
    print(f"JSON report written to: {output_path.relative_to(project_root)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
