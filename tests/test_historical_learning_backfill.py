from __future__ import annotations

import json
from pathlib import Path

from scripts.historical_learning_backfill import run_pipeline


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_trades_payload() -> dict:
    return {
        "trades": [
            {
                "symbol": "SPY",
                "strategy": "iron_condor",
                "status": "closed",
                "outcome": "win",
                "realized_pnl": 41.0,
                "entry_date": "2026-01-22",
                "exit_date": "2026-02-06",
            },
            {
                "symbol": "IWM",
                "strategy": "credit_spread",
                "status": "closed",
                "outcome": "loss",
                "realized_pnl": -23.5,
                "entry_date": "2026-01-28",
                "exit_date": "2026-02-04",
            },
            {
                "symbol": "QQQ",
                "strategy": "credit_spread",
                "status": "closed",
                "outcome": "breakeven",
                "realized_pnl": 0.0,
                "entry_date": "2026-01-29",
                "exit_date": "2026-02-05",
            },
        ]
    }


def test_backfill_dry_run_counts_without_writes(tmp_path: Path) -> None:
    trades_path = tmp_path / "data" / "trades.json"
    _write_json(trades_path, _sample_trades_payload())
    summary = run_pipeline(
        project_root=tmp_path,
        trades_path=trades_path,
        lesson_path=tmp_path / "rag_knowledge" / "lessons_learned" / "ll_test.md",
        audit_log_path=tmp_path / "data" / "feedback" / "historical.jsonl",
        recompute_model=False,
        rebuild_rag_index_flag=False,
        dry_run=True,
    )
    assert summary["closed_trades_scanned"] == 3
    assert summary["eligible_events"] == 2
    assert summary["positive_events"] == 1
    assert summary["negative_events"] == 1
    assert summary["neutral_events_skipped"] == 1
    assert summary["applied_events"] == 0
    assert not (tmp_path / "data" / "feedback" / "historical.jsonl").exists()
    assert not (tmp_path / "rag_knowledge" / "lessons_learned" / "ll_test.md").exists()


def test_backfill_is_idempotent_via_event_keys(tmp_path: Path) -> None:
    trades_path = tmp_path / "data" / "trades.json"
    _write_json(trades_path, _sample_trades_payload())
    lesson = tmp_path / "rag_knowledge" / "lessons_learned" / "ll_test.md"
    audit = tmp_path / "data" / "feedback" / "historical.jsonl"

    first = run_pipeline(
        project_root=tmp_path,
        trades_path=trades_path,
        lesson_path=lesson,
        audit_log_path=audit,
        recompute_model=False,
        rebuild_rag_index_flag=False,
        dry_run=False,
    )
    second = run_pipeline(
        project_root=tmp_path,
        trades_path=trades_path,
        lesson_path=lesson,
        audit_log_path=audit,
        recompute_model=False,
        rebuild_rag_index_flag=False,
        dry_run=False,
    )

    assert first["applied_events"] == 2
    assert first["duplicate_events"] == 0
    assert second["applied_events"] == 0
    assert second["duplicate_events"] == 2


def test_backfill_writes_lesson_with_strategy_breakdown(tmp_path: Path) -> None:
    trades_path = tmp_path / "data" / "trades.json"
    _write_json(trades_path, _sample_trades_payload())
    lesson = tmp_path / "rag_knowledge" / "lessons_learned" / "ll_test.md"
    audit = tmp_path / "data" / "feedback" / "historical.jsonl"

    summary = run_pipeline(
        project_root=tmp_path,
        trades_path=trades_path,
        lesson_path=lesson,
        audit_log_path=audit,
        recompute_model=False,
        rebuild_rag_index_flag=False,
        dry_run=False,
    )

    assert summary["strategy_breakdown"]
    text = lesson.read_text(encoding="utf-8")
    assert "Historical Learning Backfill (Automated)" in text
    assert "iron_condor" in text
    assert "credit_spread" in text
