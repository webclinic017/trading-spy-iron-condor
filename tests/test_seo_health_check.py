from __future__ import annotations

from pathlib import Path

import pytest

from scripts.seo_health_check import (
    SEOIssue,
    audit_post,
    calculate_score,
    check_canonical_url,
    check_image_alt_text,
    check_internal_links,
    check_meta_description,
    check_tags,
    check_title,
    extract_frontmatter,
)


@pytest.fixture
def temp_post(tmp_path: Path) -> Path:
    """Create a temporary blog post for testing."""
    post = tmp_path / "2026-02-18-test-post.md"
    post.write_text(
        """---
title: "Test Post"
description: "This is a test description that is long enough for SEO best practices and should pass validation checks."
tags: ["ai", "trading"]
canonical_url: "https://igorganapolsky.github.io/trading/2026/02/18/test-post/"
---

# Test Post

This is the body of the post with an [internal link](/2026/02/17/another-post/) and proper formatting.

![Alt text here](https://example.com/image.jpg)
"""
    )
    return post


def test_extract_frontmatter():
    """Test frontmatter extraction."""
    content = """---
title: "Example"
description: "A test"
tags: ["foo", "bar"]
---

Body here
"""
    fm = extract_frontmatter(content)
    assert fm["title"] == "Example"
    assert fm["description"] == "A test"


def test_check_title_missing():
    """Test title validation when missing."""
    issue = check_title({}, Path("test.md"))
    assert issue is not None
    assert issue.severity == "error"
    assert "Missing title" in issue.message


def test_check_title_too_long():
    """Test title validation when too long."""
    issue = check_title(
        {"title": "A" * 70},
        Path("test.md"),
    )
    assert issue is not None
    assert issue.severity == "warning"
    assert "too long" in issue.message


def test_check_title_valid():
    """Test title validation when valid."""
    issue = check_title({"title": "Valid Title"}, Path("test.md"))
    assert issue is None


def test_check_meta_description_missing():
    """Test meta description when missing."""
    issue = check_meta_description({}, Path("test.md"))
    assert issue is not None
    assert issue.severity == "warning"
    assert "Missing meta description" in issue.message


def test_check_meta_description_too_short():
    """Test meta description when too short."""
    issue = check_meta_description({"description": "Short"}, Path("test.md"))
    assert issue is not None
    assert "too short" in issue.message


def test_check_meta_description_too_long():
    """Test meta description when too long."""
    issue = check_meta_description({"description": "A" * 200}, Path("test.md"))
    assert issue is not None
    assert issue.severity == "info"
    assert "too long" in issue.message


def test_check_meta_description_valid():
    """Test meta description when valid."""
    issue = check_meta_description(
        {
            "description": "A valid description that is between 50 and 160 characters long for optimal SEO performance."
        },
        Path("test.md"),
    )
    assert issue is None


def test_check_canonical_url_invalid_protocol():
    """Test canonical URL with invalid protocol."""
    issue = check_canonical_url({"canonical_url": "http://example.com"}, Path("test.md"))
    assert issue is not None
    assert issue.severity == "error"
    assert "Invalid canonical URL" in issue.message


def test_check_canonical_url_missing_trailing_slash():
    """Test canonical URL without trailing slash."""
    issue = check_canonical_url(
        {"canonical_url": "https://example.com/post"},
        Path("test.md"),
    )
    assert issue is not None
    assert issue.severity == "warning"
    assert "should end with /" in issue.message


def test_check_canonical_url_valid():
    """Test valid canonical URL."""
    issue = check_canonical_url(
        {"canonical_url": "https://example.com/post/"},
        Path("test.md"),
    )
    assert issue is None


def test_check_tags_missing():
    """Test tags validation when missing."""
    issue = check_tags({}, Path("test.md"))
    assert issue is not None
    assert issue.severity == "warning"
    assert "No tags" in issue.message


def test_check_tags_present():
    """Test tags validation when present."""
    issue = check_tags({"tags": ["foo", "bar"]}, Path("test.md"))
    assert issue is None


def test_check_internal_links_none():
    """Test internal link check when none present."""
    content = """---
title: Test
---

Body with no links.
"""
    issue = check_internal_links(content, Path("test.md"))
    assert issue is not None
    assert issue.severity == "info"
    assert "No internal links" in issue.message


def test_check_internal_links_present():
    """Test internal link check when links present."""
    content = """---
title: Test
---

Body with [link](/2026/01/01/post/).
"""
    issue = check_internal_links(content, Path("test.md"))
    assert issue is None


def test_check_image_alt_text_missing():
    """Test image alt text check when missing."""
    content = """---
title: Test
---

![](https://example.com/image.jpg)
"""
    issue = check_image_alt_text(content, Path("test.md"))
    assert issue is not None
    assert issue.severity == "warning"
    assert "missing alt text" in issue.message


def test_check_image_alt_text_present():
    """Test image alt text check when present."""
    content = """---
title: Test
---

![Alt text](https://example.com/image.jpg)
"""
    issue = check_image_alt_text(content, Path("test.md"))
    assert issue is None


def test_calculate_score_perfect():
    """Test score calculation with no issues."""
    assert calculate_score([]) == 100


def test_calculate_score_with_errors():
    """Test score calculation with errors."""
    issues = [
        SEOIssue("error", "test.md", "Error 1"),
        SEOIssue("error", "test.md", "Error 2"),
    ]
    assert calculate_score(issues) == 60  # 100 - (2 * 20)


def test_calculate_score_with_warnings():
    """Test score calculation with warnings."""
    issues = [
        SEOIssue("warning", "test.md", "Warning 1"),
        SEOIssue("warning", "test.md", "Warning 2"),
    ]
    assert calculate_score(issues) == 90  # 100 - (2 * 5)


def test_calculate_score_mixed():
    """Test score calculation with mixed issues."""
    issues = [
        SEOIssue("error", "test.md", "Error"),
        SEOIssue("warning", "test.md", "Warning"),
        SEOIssue("info", "test.md", "Info"),
    ]
    assert calculate_score(issues) == 74  # 100 - 20 - 5 - 1


def test_audit_post_valid(temp_post: Path):
    """Test auditing a valid post."""
    issues = audit_post(temp_post)
    # Should have minimal issues (maybe info about internal links)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0


def test_audit_post_nonexistent():
    """Test auditing a nonexistent post."""
    issues = audit_post(Path("/nonexistent/post.md"))
    assert issues == []
