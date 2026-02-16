"""Tests for sync_rag_to_blog.py script."""

import tempfile
from pathlib import Path


def test_parse_lesson_file():
    """Test parsing a lesson file."""
    from scripts.sync_rag_to_blog import parse_lesson_file

    # Create temp lesson file
    with tempfile.NamedTemporaryFile(mode="w", suffix="_jan13.md", delete=False) as f:
        f.write(
            """# Test Lesson Title

**Severity**: CRITICAL
**Category**: testing

This is the content.
"""
        )
        temp_path = Path(f.name)

    try:
        result = parse_lesson_file(temp_path)
        assert result is not None
        assert result["severity"] == "CRITICAL"
        assert "2026-01-13" in result["date"]
        assert "Test Lesson Title" in result["title"]
    finally:
        temp_path.unlink()


def test_parse_lesson_file_low_severity():
    """Test parsing lesson with no explicit severity defaults to LOW."""
    from scripts.sync_rag_to_blog import parse_lesson_file

    with tempfile.NamedTemporaryFile(mode="w", suffix="_jan12.md", delete=False) as f:
        f.write("# Simple Lesson\n\nJust content here.")
        temp_path = Path(f.name)

    try:
        result = parse_lesson_file(temp_path)
        assert result["severity"] == "LOW"
    finally:
        temp_path.unlink()


def test_truncate_at_sentence_short_text():
    """Short text returned as-is."""
    from scripts.sync_rag_to_blog import _truncate_at_sentence

    assert _truncate_at_sentence("Hello world.", max_chars=250) == "Hello world."


def test_truncate_at_sentence_boundary():
    """Text truncated at sentence boundary."""
    from scripts.sync_rag_to_blog import _truncate_at_sentence

    text = "First sentence here. Second sentence is longer and should be cut. Third sentence too."
    result = _truncate_at_sentence(text, max_chars=65)
    assert result == "First sentence here. Second sentence is longer and should be cut."


def test_truncate_at_sentence_word_boundary_fallback():
    """Falls back to word boundary when no sentence ending found."""
    from scripts.sync_rag_to_blog import _truncate_at_sentence

    text = "This is a long sentence without any period that goes on and on and on"
    result = _truncate_at_sentence(text, max_chars=40)
    assert result.endswith("...")
    assert len(result) <= 43  # 40 chars + "..."


def test_generate_daily_summary_post():
    """Test blog post generation."""
    from scripts.sync_rag_to_blog import generate_daily_summary_post

    lessons = [
        {
            "id": "ll_001",
            "title": "Test Lesson",
            "severity": "HIGH",
            "content": "This is test content for the lesson.",
        },
        {
            "id": "ll_002",
            "title": "Another Lesson",
            "severity": "LOW",
            "content": "More test content.",
        },
    ]

    post = generate_daily_summary_post("2026-01-13", lessons)

    assert "Day" in post
    assert "2026-01-13" in post
    assert "Lessons Learned" in post
    assert "**2**" in post  # 2 lessons (bold in table)
    assert "Test Lesson" in post
    assert "Important Discoveries" in post or "Hard Lessons" in post


def test_no_of_90_past_day_90():
    """Past day 90, posts should NOT say 'of 90' or '0 days remaining'."""
    from scripts.sync_rag_to_blog import generate_daily_summary_post

    lessons = [
        {
            "id": "ll_001",
            "title": "Late Lesson",
            "severity": "LOW",
            "content": "Content for a late lesson.",
        },
    ]

    # Feb 15, 2026 = Day 110 (well past 90)
    post = generate_daily_summary_post("2026-02-15", lessons)

    assert "of 90" not in post
    assert "0 days remaining" not in post
    assert "Day 110" in post


def test_no_boilerplate_sections():
    """Daily posts should NOT contain the old boilerplate sections."""
    from scripts.sync_rag_to_blog import generate_daily_summary_post

    lessons = [
        {
            "id": "ll_001",
            "title": "Test",
            "severity": "LOW",
            "content": "Content.",
        },
    ]

    post = generate_daily_summary_post("2026-01-13", lessons)

    assert "Tech Stack Behind the Lessons" not in post
    assert "The Journey So Far" not in post
    assert "How We Learn Autonomously" not in post


def test_varied_intros():
    """Different days with different lesson counts produce different intros."""
    from scripts.sync_rag_to_blog import get_engaging_intro

    intro1 = get_engaging_intro(
        50,
        "Monday",
        [{"severity": "LOW", "title": "A", "content": "x"}],
    )
    intro2 = get_engaging_intro(
        51,
        "Tuesday",
        [
            {"severity": "CRITICAL", "title": "B", "content": "y"},
            {"severity": "CRITICAL", "title": "C", "content": "z"},
        ],
    )

    # Different inputs should produce different intros
    assert intro1 != intro2
