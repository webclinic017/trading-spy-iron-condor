#!/usr/bin/env python3
"""
Tests for scripts/fix_blog_posts_for_lint.py

Goal: ensure the fixer is deterministic/idempotent and produces content that
passes scripts/lint_blog_posts.py strict checks.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


@pytest.fixture(scope="module")
def fixer():
    return _load_module("fix_blog_posts_for_lint", "scripts/fix_blog_posts_for_lint.py")


@pytest.fixture(scope="module")
def blog_linter():
    return _load_module("lint_blog_posts", "scripts/lint_blog_posts.py")


def test_fix_post_makes_lint_pass(fixer, blog_linter, tmp_path: Path):
    p = tmp_path / "post.md"
    p.write_text(
        "\n".join(
            [
                "---",
                'title: "RLHF WIN: FAST FEEDBACK LOOP"',
                "date: 2026-02-03",
                "---",
                "",
                "# RLHF WIN: FAST FEEDBACK LOOP",
                "",
                # Ensure we clear the strict linter's "<200 words" warning.
                " ".join(
                    [
                        "This is an engineering note about changes in the trading system."
                        " It exists only for tests and is intentionally repetitive."
                    ]
                    * 60
                ),
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    changed = fixer.fix_post(p)
    assert changed is True

    issues = blog_linter.lint_file(p)
    assert issues == [], f"expected no lint issues, got: {issues}"


def test_fix_post_is_idempotent(fixer, blog_linter, tmp_path: Path):
    p = tmp_path / "post.md"
    p.write_text(
        "\n".join(
            [
                "---",
                'title: "Tars Routing Update"',
                'description: "A description exists."',
                'image: "/assets/snapshots/progress_latest.png"',
                "---",
                "",
                "# Tars Routing Update",
                "",
                "## Answer Block",
                "",
                "> **Answer Block:** Summary.",
                "",
                "---",
                "",
                "Evidence: https://github.com/IgorGanapolsky/trading/",
                "",
                " ".join(["Extra body content."] * 300),
                "",
            ]
        ),
        encoding="utf-8",
    )

    first = fixer.fix_post(p)
    second = fixer.fix_post(p)

    # Already compliant; the fixer should not churn files.
    assert first is False
    assert second is False
    assert blog_linter.lint_file(p) == []


def test_existing_answer_block_quote_gets_heading(fixer, blog_linter, tmp_path: Path):
    p = tmp_path / "post.md"
    p.write_text(
        "\n".join(
            [
                "---",
                'title: "Daily update"',
                "date: 2026-01-20",
                "---",
                "",
                "# Daily update",
                "",
                "> **Answer Block:** This is already here but missing the heading.",
                "",
                "Evidence: https://github.com/IgorGanapolsky/trading/",
                "",
                " ".join(["Extra body content."] * 300),
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    changed = fixer.fix_post(p)
    assert changed is True
    assert "## Answer Block" in p.read_text(encoding="utf-8")
    assert blog_linter.lint_file(p) == []
