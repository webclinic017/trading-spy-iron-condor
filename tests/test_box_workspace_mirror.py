"""Tests for box workspace mirror manifest generation."""

from __future__ import annotations

from pathlib import Path

from scripts.box_workspace_mirror import (
    MirrorEntry,
    build_manifest_entries,
    collect_workspace_files,
    file_sha256,
)


def test_collect_workspace_files_respects_include_exclude(tmp_path: Path):
    (tmp_path / "artifacts" / "devloop").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "devloop" / "report.md").write_text("hello", encoding="utf-8")
    (tmp_path / "artifacts" / "devloop" / "debug.log").write_text("noise", encoding="utf-8")
    (tmp_path / "wiki").mkdir(parents=True, exist_ok=True)
    (tmp_path / "wiki" / "Progress-Dashboard.md").write_text("dashboard", encoding="utf-8")

    files = collect_workspace_files(
        repo_root=tmp_path,
        include_patterns=["artifacts/devloop/**/*", "wiki/Progress-Dashboard.md"],
        exclude_patterns=["**/*.log"],
        max_file_bytes=1024 * 1024,
    )
    rel = [str(path.relative_to(tmp_path)) for path in files]
    assert "artifacts/devloop/report.md" in rel
    assert "wiki/Progress-Dashboard.md" in rel
    assert "artifacts/devloop/debug.log" not in rel


def test_build_manifest_entries_contains_sha_and_size(tmp_path: Path):
    target = tmp_path / "data.json"
    target.write_text('{"ok":true}\n', encoding="utf-8")

    entries = build_manifest_entries(tmp_path, [target])
    assert len(entries) == 1
    entry: MirrorEntry = entries[0]
    assert entry.path == "data.json"
    assert entry.size_bytes > 0
    assert entry.sha256 == file_sha256(target)
    assert entry.modified_utc
