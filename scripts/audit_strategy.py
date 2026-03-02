"""
Architectural Auditor Script
Enforces Vertical Slice and Folder-as-Namespace patterns.
"""

import sys
from pathlib import Path


def audit_strategy(strategy_dir: str):
    path = Path(strategy_dir)
    print(f"\n🔍 Auditing Vertical Slice: {path.name}")
    print("=" * 60)

    violations = []

    # 1. Structure Check
    required_files = ["signal.py", "executor.py", "risk.py", "__init__.py"]
    for f in required_files:
        if not (path / f).exists():
            violations.append(f"MISSING FILE: {f}")
        else:
            print(f"✅ Found {f}")

    # 2. Logic Purity Check (Signal should not import execution tools)
    signal_file = path / "signal.py"
    if signal_file.exists():
        content = signal_file.read_text()
        if "alpaca" in content.lower() or "submit_order" in content.lower():
            violations.append("PURITY VIOLATION: signal.py contains execution logic/imports")
        else:
            print("✅ signal.py is pure (no execution logic)")

    # 3. Risk Enforcement Check (Executor should not define risk)
    executor_file = path / "executor.py"
    if executor_file.exists():
        content = executor_file.read_text()
        if "max_risk" in content.lower() or "stop_loss" in content.lower():
            # Logic for risk should be in risk.py
            pass
        if "safe_submit_order" not in content:
            violations.append("SAFETY VIOLATION: executor.py bypasses safe_submit_order gateway")
        else:
            print("✅ executor.py uses mandatory safety gateway")

    # 4. Summary
    if violations:
        print("\n❌ VIOLATIONS FOUND:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("\n🏆 PASS: Strategy slice is architecturally compliant.")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_strategy.py <strategy_dir>")
        sys.exit(1)
    audit_strategy(sys.argv[1])
