#!/usr/bin/env python3
"""
Test RLHF Blog Publisher - CI Enforcement

Ensures the blog publishing system stays functional.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestRLHFBlogPublisher:
    """Enforce RLHF blog system stays functional."""

    def test_blog_script_exists(self):
        """Ensure blog publishing script exists."""
        script = Path("scripts/publish_rlhf_blog.py")
        assert script.exists(), "RLHF blog publishing script missing!"

    def test_blog_workflow_exists(self):
        """Ensure blog workflow exists."""
        workflow = Path(".github/workflows/rlhf-blog-publisher.yml")
        assert workflow.exists(), "RLHF blog workflow missing!"

    def test_blog_script_imports(self):
        """Ensure blog script can be imported."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "publish_rlhf_blog", "scripts/publish_rlhf_blog.py"
        )
        assert spec is not None, "Cannot load blog script"
        assert spec.loader is not None, "Blog script has no loader"

    def test_blog_script_runs_dry(self):
        """Ensure blog script runs in dry-run mode without errors."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/publish_rlhf_blog.py",
                "--signal",
                "positive",
                "--intensity",
                "0.5",
                "--context",
                "CI test run",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"Blog script failed: {result.stderr}"
        assert "Generated" in result.stdout, "Blog post not generated"

    def test_blog_script_handles_negative_signal(self):
        """Ensure blog script handles negative signals."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/publish_rlhf_blog.py",
                "--signal",
                "negative",
                "--intensity",
                "0.7",
                "--context",
                "CI negative test",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"Blog script failed on negative: {result.stderr}"
        assert "lesson" in result.stdout.lower(), "Negative post should mention lesson"

    def test_blog_posts_directory_exists(self):
        """Ensure blog posts directory exists."""
        posts_dir = Path("docs/_posts")
        assert posts_dir.exists(), "Blog posts directory missing!"

    def test_feedback_log_exists(self):
        """Ensure feedback log can be created."""
        log_dir = Path(".claude/memory/feedback")
        assert log_dir.exists() or log_dir.parent.exists(), "Feedback directory missing!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
