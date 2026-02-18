"""Tests for autonomous meta description generator."""

from pathlib import Path

import pytest

from scripts.add_meta_descriptions import extract_description_from_content, extract_frontmatter


def test_extract_answer_block():
    """Extract description from Answer Block (priority 1)."""
    body = """
> **Answer Block:** This is a concise summary of the post content.

# Main Content

Some other text here.
"""
    desc = extract_description_from_content(body, max_length=160)
    assert desc == "This is a concise summary of the post content."


def test_extract_first_paragraph():
    """Extract description from first substantive paragraph (priority 2)."""
    body = """
# Heading

This is the first paragraph with meaningful content. It should be used as the description.

## Another Section

More text here.
"""
    desc = extract_description_from_content(body, max_length=160)
    assert desc == "This is the first paragraph with meaningful content. It should be used as the description."


def test_truncate_long_content():
    """Truncate long descriptions to max_length."""
    body = "A" * 200
    desc = extract_description_from_content(body, max_length=160)
    assert len(desc) <= 160


def test_extract_frontmatter_valid():
    """Extract valid YAML frontmatter."""
    content = """---
layout: post
title: Test Post
tags: ["ai", "trading"]
---

# Content
"""
    fm, body = extract_frontmatter(content)
    assert fm["layout"] == "post"
    assert fm["title"] == "Test Post"
    assert fm["tags"] == ["ai", "trading"]
    assert body.startswith("# Content")


def test_extract_frontmatter_yaml_list():
    """Extract YAML list format tags."""
    content = """---
layout: post
tags:
- ai
- trading
---

# Content
"""
    fm, body = extract_frontmatter(content)
    assert fm["tags"] == ["ai", "trading"]


def test_extract_frontmatter_invalid():
    """Handle invalid frontmatter gracefully."""
    content = "# Just a heading\n\nNo frontmatter here."
    fm, body = extract_frontmatter(content)
    assert fm == {}
    assert body == content


def test_skip_markdown_formatting():
    """Clean markdown formatting from descriptions."""
    body = """
This is a paragraph with **bold** and *italic* and `code` formatting.
"""
    desc = extract_description_from_content(body, max_length=160)
    assert "**" not in desc
    assert "*" not in desc
    assert "`" not in desc
