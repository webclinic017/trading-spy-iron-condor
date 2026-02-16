"""Tests for scripts.agent_workflow_toolkit."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scripts.agent_workflow_toolkit import (
    RetroCapture,
    build_context_bundle,
    build_retro_markdown,
    build_zsh_snippet,
    parse_plan_tasks,
    run_chain,
    slim_log_text,
    write_retro_files,
)


def test_slim_log_text_redacts_and_compresses():
    raw = "\n".join(
        [
            "2026-02-16T15:00:00Z INFO API_KEY=abc123xyz",
            "2026-02-16T15:00:01Z INFO API_KEY=abc123xyz",
            "2026-02-16T15:00:02Z ERROR bearer super-secret-token",
        ]
    )

    slimmed = slim_log_text(raw, max_lines=10, max_chars=1000)

    assert "I API_KEY=[REDACTED]" in slimmed
    assert "E bearer [REDACTED]" in slimmed
    assert "(x2)" in slimmed
    assert "2026-02-16" not in slimmed


def test_build_context_bundle_enforces_token_budget():
    bundle, stats = build_context_bundle(
        sections=[
            ("a.txt", "alpha\n" * 30),
            ("b.txt", "beta\n" * 30),
        ],
        max_tokens=90,
        max_chars_per_section=1000,
        line_numbers=False,
    )

    assert stats.included_sections >= 1
    assert stats.skipped_sections >= 1
    assert "## a.txt" in bundle
    assert "## Bundle Stats" in bundle


def test_parse_plan_tasks_extracts_checkbox_numbered_and_bullets():
    plan = "\n".join(
        [
            "# Plan",
            "- [ ] First step",
            "2. Second step",
            "- Third step",
        ]
    )

    tasks = parse_plan_tasks(plan, max_tasks=5)
    assert tasks == ["First step", "Second step", "Third step"]


def test_retro_files_are_written_with_rag_tags(tmp_path: Path):
    capture = RetroCapture(
        wins=["CI stayed green"],
        frictions=["Noisy logs slowed debugging"],
        actions=["Use slim-logs before asking agents to diagnose failures"],
    )
    markdown = build_retro_markdown(entry_date=date(2026, 2, 16), capture=capture)
    artifact_path, rag_path = write_retro_files(
        repo_root=tmp_path,
        entry_date=date(2026, 2, 16),
        retro_markdown=markdown,
    )

    assert artifact_path.exists()
    assert rag_path.exists()
    rag_text = rag_path.read_text(encoding="utf-8")
    assert "LL-Agentic-Retro-20260216" in rag_text
    assert "`agentic-workflow`" in rag_text


def test_run_chain_dry_run_writes_artifacts(tmp_path: Path):
    exit_code, run_dir = run_chain(
        task="Improve build reliability",
        planner_command="cat",
        executor_command="cat",
        output_dir=tmp_path / "runs",
        workdir=tmp_path,
        max_tasks=4,
        dry_run=True,
    )

    assert exit_code == 0
    assert (run_dir / "plan.md").exists()
    assert (run_dir / "execution.md").exists()
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["dry_run"] is True
    assert summary["failed_tasks"] == 0


def test_build_zsh_snippet_contains_expected_shortcuts(tmp_path: Path):
    snippet = build_zsh_snippet(toolkit_path=tmp_path / "scripts" / "agent_workflow_toolkit.py")
    assert "x() {" in snippet
    assert "funked() {" in snippet
    assert "s() { source" in snippet
    assert "chainagents() {" in snippet
