#!/usr/bin/env python3
"""Batch add tags to lessons-learned posts for SEO optimization."""

import re
from pathlib import Path

# Standard tags for lessons-learned daily journal posts
LESSONS_TAGS = ["lessons-learned", "daily-journal", "ai-trading", "building-in-public"]


def update_frontmatter_tags(file_path: Path) -> bool:
    """Add tags to frontmatter if missing."""
    content = file_path.read_text()

    # Check if already has tags
    if re.search(r"^tags:\s*\[.+\]", content, re.MULTILINE):
        return False  # Already has tags

    # Find frontmatter end
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"⚠️  Skipping {file_path.name} - invalid frontmatter")
        return False

    frontmatter = parts[1]
    body = parts[2]

    # Add tags before frontmatter end
    tags_line = f"tags: {LESSONS_TAGS}\n"
    updated_frontmatter = frontmatter.rstrip() + f"\n{tags_line}"

    # Reconstruct file
    updated_content = f"---{updated_frontmatter}---{body}"
    file_path.write_text(updated_content)

    return True


def main():
    """Process all lessons-learned posts."""
    posts_dir = Path("docs/_posts")
    lessons_files = sorted(posts_dir.glob("*lessons-learned.md"))

    updated = 0
    skipped = 0

    print(f"Found {len(lessons_files)} lessons-learned posts")
    print(f"Adding tags: {LESSONS_TAGS}\n")

    for file_path in lessons_files:
        if update_frontmatter_tags(file_path):
            print(f"✅ {file_path.name}")
            updated += 1
        else:
            print(f"⏭️  {file_path.name} (already has tags)")
            skipped += 1

    print(f"\n{'=' * 60}")
    print(f"Updated: {updated} files")
    print(f"Skipped: {skipped} files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
