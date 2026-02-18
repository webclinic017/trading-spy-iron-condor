"""Integration test: OrchestratorTelemetry -> session_decisions -> North Star gate diagnostics."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.orchestrator.telemetry import OrchestratorTelemetry
from src.safety.north_star_operating_plan import compute_weekly_gate


def test_telemetry_session_decisions_feed_no_trade_diagnostic(tmp_path, monkeypatch):
    """Ensure saved session decisions are discoverable by weekly gate diagnostics."""
    monkeypatch.chdir(tmp_path)
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Weekly gate expects trades.json in the same directory as session_decisions_*.json
    (data_dir / "trades.json").write_text(json.dumps({"trades": []}), encoding="utf-8")

    telemetry = OrchestratorTelemetry()
    telemetry.start_ticker_decision("SPY")
    telemetry.update_ticker_decision(
        "SPY",
        gate=1,
        status="REJECT",
        rejection_reason="VIX 12.0 < 15.0 (premiums too thin)",
        indicators={"volume_ratio": 0.1},
    )
    telemetry.save_session_decisions({"session_type": "test", "is_market_day": True})

    session_files = sorted(data_dir.glob("session_decisions_*.json"))
    assert session_files, "Expected a session_decisions_*.json artifact"

    # Use the artifact date for deterministic gate evaluation.
    session_date = session_files[0].stem.replace("session_decisions_", "", 1)
    today = date.fromisoformat(session_date)

    gate, _history = compute_weekly_gate(
        {"paper_account": {"win_rate": 0.0, "win_rate_sample_size": 0, "total_pl": 0.0}},
        trades_path=data_dir / "trades.json",
        weekly_history_path=data_dir / "north_star_weekly_history.json",
        today=today,
    )

    cadence = gate.get("cadence_kpi", {})
    assert cadence.get("qualified_setups_observed") == 1

    diagnostic = gate.get("no_trade_diagnostic", {})
    assert diagnostic.get("decision_records_observed") >= 1
    top_reasons = diagnostic.get("top_rejection_reasons", [])
    assert isinstance(top_reasons, list)
    assert any("VIX" in str(item.get("reason", "")) for item in top_reasons)
