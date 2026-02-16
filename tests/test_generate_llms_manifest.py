"""Tests for scripts/generate_llms_manifest.py."""

from pathlib import Path

from scripts.generate_llms_manifest import _write_if_changed, generate_manifests


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_generate_manifests_indexes_site_and_repo_content(tmp_path: Path) -> None:
    root = tmp_path

    _write(
        root / "docs/_posts/2026-02-15-my-latest-post.md",
        "---\n"
        "title: My Latest Post\n"
        "---\n"
        "\n"
        "# Body\n",
    )
    _write(
        root / "docs/_posts/2026-02-14-older-post.md",
        "# Older Post\n",
    )
    _write(
        root / "docs/_reports/daily-report.md",
        "---\n"
        "title: Daily Report\n"
        "---\n",
    )
    _write(
        root / "rag_knowledge/lessons_learned/LL-001.md",
        "# LL-001: Test Lesson\n\n"
        "**Date**: 2026-02-13\n",
    )
    _write(root / ".github/workflows/ci.yml", "name: CI\n")
    _write(root / ".github/workflows/deploy-pages.yml", "name: Deploy\n")

    summary, full = generate_manifests(
        root=root,
        site_url="https://example.com/trading",
        repo_url="https://github.com/example/trading",
    )

    assert "# AI Trading Journey - LLM Index" in summary
    assert "Blog posts published: 2" in summary
    assert "Reports published: 1" in summary
    assert "Lessons in RAG markdown: 1" in summary
    assert "Automation workflows: 2" in summary
    assert "[My Latest Post](https://example.com/trading/2026/02/15/my-latest-post.html)" in summary

    assert "# AI Trading Journey - Full LLM Catalog" in full
    assert "Blog posts indexed: 2" in full
    assert "Lessons indexed: 1" in full
    assert "https://example.com/trading/llms.txt" in full
    assert (
        "[LL-001: Test Lesson]"
        "(https://github.com/example/trading/blob/main/rag_knowledge/lessons_learned/LL-001.md)"
        in full
    )


def test_write_if_changed_check_mode_is_non_destructive(tmp_path: Path) -> None:
    target = tmp_path / "docs/llms.txt"

    changed = _write_if_changed(target, "first\n", check=False)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "first\n"

    changed = _write_if_changed(target, "first\n", check=True)
    assert changed is False
    assert target.read_text(encoding="utf-8") == "first\n"

    changed = _write_if_changed(target, "second\n", check=True)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "first\n"
