#!/usr/bin/env python3
"""
Autonomous meta description generator for blog posts.
Extracts meaningful content and generates SEO-optimized descriptions (120-160 chars).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown content."""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def extract_description_from_content(body: str, max_length: int = 160) -> str:
    """
    Extract or generate description from post content.
    Priority: Answer Block > First paragraph > First heading.
    """
    # Priority 1: Answer Block (these are SEO-optimized summaries)
    answer_block = re.search(
        r"> \*\*Answer Block:\*\* (.+?)(?:\n\n|\n>|$)", body, re.DOTALL
    )
    if answer_block:
        desc = answer_block.group(1).strip()
        desc = re.sub(r"\n+", " ", desc)  # Remove newlines
        desc = re.sub(r"\s+", " ", desc)  # Normalize spaces
        if len(desc) <= max_length:
            return desc
        # Truncate at sentence boundary
        sentences = re.split(r"(?<=[.!?])\s+", desc)
        result = sentences[0]
        for sentence in sentences[1:]:
            if len(result) + len(sentence) + 1 <= max_length:
                result += " " + sentence
            else:
                break
        return result[:max_length].rstrip()

    # Priority 2: First substantive paragraph (skip short lines)
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    for para in paragraphs:
        # Skip markdown headers, blockquotes, code blocks
        if para.startswith(("#", ">", "```", "|", "-")):
            continue
        # Clean markdown formatting
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", para)  # Links
        clean = re.sub(r"[*_`]", "", clean)  # Bold, italic, code
        clean = re.sub(r"\s+", " ", clean).strip()

        if len(clean) >= 60:  # Minimum meaningful length
            if len(clean) <= max_length:
                return clean
            # Truncate at sentence boundary
            sentences = re.split(r"(?<=[.!?])\s+", clean)
            result = sentences[0]
            if len(result) > max_length:
                return result[:max_length - 3] + "..."
            return result

    # Priority 3: Fallback - use title context
    return "Engineering lessons from building an AI-powered trading system with Claude and Python."


def add_description_to_post(file_path: Path) -> bool:
    """Add meta description to post if missing."""
    content = file_path.read_text()
    frontmatter, body = extract_frontmatter(content)

    # Skip if already has description or excerpt
    if frontmatter.get("description") or frontmatter.get("excerpt"):
        return False

    # Generate description
    description = extract_description_from_content(body, max_length=160)

    # Add to frontmatter
    frontmatter["description"] = description

    # Reconstruct file
    fm_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    updated_content = f"---\n{fm_str}---\n\n{body}"
    file_path.write_text(updated_content)

    return True


def main():
    """Process all posts missing descriptions."""
    posts_dir = Path("docs/_posts")

    # Get list of posts missing descriptions from SEO check
    missing_files = [
        "2026-01-14-100k-lessons-we-lost.md",
        "2026-01-14-all-rag-lessons-published.md",
        "2026-01-22-position-stacking-disaster-fix.md",
        "2026-01-22-ralph-discovery.md",
        "2026-01-23-ralph-discovery.md",
        "2026-01-24-ralph-discovery.md",
        "2026-01-25-ralph-discovery.md",
        "2026-01-25-ralph-weekly-digest.md",
        "2026-01-26-ralph-discovery.md",
        "2026-01-27-ralph-discovery.md",
        "2026-01-28-ralph-discovery.md",
        "2026-01-28-technical-debt-audit.md",
        "2026-01-29-ralph-discovery.md",
        "2026-01-30-ralph-discovery.md",
        "2026-01-31-ralph-discovery.md",
        "2026-02-01-ralph-discovery.md",
        "2026-02-01-ralph-weekly-digest.md",
        "2026-02-03-rlhf-win-1524.md",
        "2026-02-03-rlhf-win.md",
        "2026-02-04-rlhf-win-1728.md",
    ]

    updated = 0
    skipped = 0

    print("Adding meta descriptions to blog posts...\n")

    for filename in missing_files:
        file_path = posts_dir / filename

        if not file_path.exists():
            print(f"⚠️  {filename} not found")
            continue

        if add_description_to_post(file_path):
            # Read back to show description
            content = file_path.read_text()
            fm, _ = extract_frontmatter(content)
            desc = fm.get("description", "")
            print(f"✅ {filename}")
            print(f"   → {desc} ({len(desc)} chars)")
            updated += 1
        else:
            print(f"⏭️  {filename} (already has description)")
            skipped += 1

    print(f"\n{'=' * 60}")
    print(f"Updated: {updated} files")
    print(f"Skipped: {skipped} files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
