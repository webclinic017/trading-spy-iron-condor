#!/usr/bin/env python3
"""
AI-powered SEO enhancements for blog posts.

Features:
1. Auto-generate optimized meta descriptions (120-160 chars)
2. Suggest internal links to related posts
3. Recommend keywords based on content analysis

Requires: ANTHROPIC_API_KEY environment variable
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import anthropic
except ImportError:
    print("❌ anthropic not installed: pip install anthropic", file=sys.stderr)
    sys.exit(1)


DOCS_DIR = Path(__file__).parent.parent / "docs"
POSTS_DIR = DOCS_DIR / "_posts"


def extract_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
    """Extract frontmatter and body from markdown."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    fm_raw = match.group(1)
    body = match.group(2).strip()

    # Simple YAML parsing
    fm: dict[str, Any] = {}
    for line in fm_raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            if value.startswith('"') and value.endswith('"') or value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            fm[key.strip()] = value

    return fm, body


def generate_meta_description(title: str, body: str, api_key: str) -> str:
    """Generate SEO-optimized meta description using Claude."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Generate a compelling SEO meta description for this blog post.

Title: {title}

Content preview:
{body[:1000]}

Requirements:
- 120-160 characters
- Include primary keyword naturally
- Enticing, action-oriented
- No quotes or special characters
- Complete sentence

Output ONLY the meta description text, nothing else."""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast, cheap
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        description = response.content[0].text.strip()
        # Remove quotes if present
        description = description.strip('"\'')
        # Truncate if too long
        if len(description) > 160:
            description = description[:157] + "..."

        return description

    except Exception as e:
        print(f"❌ Error generating description: {e}", file=sys.stderr)
        return ""


def suggest_internal_links(title: str, body: str, existing_posts: list[Path]) -> list[dict[str, str]]:
    """Suggest internal links to related posts based on content similarity."""
    # Extract key terms from current post
    body_lower = body.lower()

    suggestions = []

    for post_file in existing_posts:
        if not post_file.exists():
            continue

        post_content = post_file.read_text()
        post_fm, post_body = extract_frontmatter_and_body(post_content)
        post_title = post_fm.get("title", "")

        if not post_title:
            continue

        # Calculate relevance score (simple keyword matching)
        score = 0

        # Check for shared keywords
        keywords = [
            "iron condor",
            "spy",
            "trading",
            "options",
            "credit spread",
            "profit",
            "loss",
            "rlhf",
            "feedback",
            "ci",
            "workflow",
            "automation",
            "ralph",
            "cto",
        ]

        for keyword in keywords:
            if keyword in body_lower and keyword in post_body.lower():
                score += 1

        if score >= 2:  # At least 2 shared keywords
            # Generate URL from filename
            stem = post_file.stem
            if len(stem) >= 11 and stem[4] == "-" and stem[7] == "-" and stem[10] == "-":
                date = stem[:10]
                slug = stem[11:]
                year, month, day = date.split("-")
                url = f"/{year}/{month}/{day}/{slug}/"

                suggestions.append(
                    {
                        "title": post_title,
                        "url": url,
                        "score": score,
                    }
                )

    # Sort by score, return top 3
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions[:3]


def suggest_keywords(title: str, body: str, api_key: str) -> list[str]:
    """Suggest SEO keywords using Claude."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze this blog post and suggest 5-7 SEO keywords/phrases.

Title: {title}

Content:
{body[:1500]}

Requirements:
- Focus on search intent
- Include long-tail keywords
- Trading/AI/tech domain
- Mix of specific and broad terms

Output as comma-separated list only."""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        keywords_raw = response.content[0].text.strip()
        keywords = [k.strip() for k in keywords_raw.split(",")]
        return keywords[:7]

    except Exception as e:
        print(f"❌ Error suggesting keywords: {e}", file=sys.stderr)
        return []


def enhance_post(post_file: Path, dry_run: bool = False) -> dict[str, Any]:
    """Enhance a single blog post with AI SEO suggestions."""
    if not post_file.exists():
        return {"error": "File not found"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}

    content = post_file.read_text()
    fm, body = extract_frontmatter_and_body(content)

    title = fm.get("title", "")
    if not title:
        return {"error": "Post missing title"}

    print(f"\n🔍 Analyzing: {post_file.name}")
    print(f"   Title: {title}")

    enhancements: dict[str, Any] = {}

    # 1. Generate meta description if missing
    current_desc = fm.get("description", "")
    if not current_desc or len(current_desc) < 50:
        print("   Generating meta description...")
        new_desc = generate_meta_description(title, body, api_key)
        if new_desc:
            enhancements["description"] = new_desc
            print(f"   ✅ Description: {new_desc}")

    # 2. Suggest internal links
    print("   Finding related posts...")
    existing_posts = [p for p in POSTS_DIR.glob("*.md") if p != post_file]
    link_suggestions = suggest_internal_links(title, body, existing_posts)
    if link_suggestions:
        enhancements["internal_links"] = link_suggestions
        print(f"   ✅ Found {len(link_suggestions)} related posts")
        for link in link_suggestions:
            print(f"      - {link['title']} ({link['url']})")

    # 3. Suggest keywords
    current_tags = fm.get("tags", "")
    if not current_tags or current_tags == "[]":
        print("   Suggesting keywords...")
        keywords = suggest_keywords(title, body, api_key)
        if keywords:
            enhancements["keywords"] = keywords
            print(f"   ✅ Keywords: {', '.join(keywords)}")

    if not dry_run and enhancements:
        print(f"\n   💾 Saving enhancements to: {post_file}.seo.json")
        seo_file = post_file.with_suffix(".md.seo.json")
        seo_file.write_text(json.dumps(enhancements, indent=2))

    return enhancements


def main() -> int:
    """Enhance blog posts with AI SEO suggestions."""
    import argparse

    parser = argparse.ArgumentParser(description="AI-powered SEO enhancement for blog posts")
    parser.add_argument("post", nargs="?", help="Path to specific post (or all if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--batch", action="store_true", help="Process all posts")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set")
        print("   Get key at: https://console.anthropic.com/")
        return 1

    posts_to_process = []

    if args.batch:
        posts_to_process = sorted(POSTS_DIR.glob("*.md"))
        print(f"📚 Processing {len(posts_to_process)} posts...")
    elif args.post:
        post_path = Path(args.post)
        if not post_path.exists():
            print(f"❌ File not found: {args.post}")
            return 1
        posts_to_process = [post_path]
    else:
        print("Usage: ai_seo_enhancer.py <post.md>")
        print("       ai_seo_enhancer.py --batch")
        return 1

    success_count = 0
    for post_file in posts_to_process:
        result = enhance_post(post_file, dry_run=args.dry_run)
        if "error" not in result and result:
            success_count += 1

    print(f"\n✅ Enhanced {success_count}/{len(posts_to_process)} posts")

    if args.dry_run:
        print("\n--- DRY RUN (not saved) ---")

    return 0


if __name__ == "__main__":
    sys.exit(main())
