#!/usr/bin/env python3
"""Shorten blog post titles for better SEO (<60 chars)."""

import re
from pathlib import Path

# Map of filename -> new shortened title
TITLE_UPDATES = {
    "2026-01-07-the-silent-74-days.md": "The Silent 74 Days: System Reported Success, Did Nothing",
    "2026-01-13-day-74-strategy-pivot-credit-spreads.md": "Day 74: The Math That Killed Our $100/Day Dream",
    "2026-01-14-cto-autonomous-decisions.md": "How I Almost Blew 48% on One Trade (Caught in Time)",
    "2026-01-21-iron-condors-ai-trading-complete-guide.md": "Complete Guide: AI-Powered Iron Condor Trading",
    "2026-01-22-position-stacking-disaster-fix.md": "LL-275: Position Stacking Disaster and Fix",
    "2026-01-24-ralph-discovery.md": "Iron Condor Optimization Research (LL-277)",
    "2026-01-25-ralph-discovery.md": "Data Sync Infrastructure Improvements (LL-262)",
    "2026-01-26-ralph-discovery.md": "Ralph Proactive Scan Findings",
    "2026-01-28-technical-debt-audit.md": "Tech Debt Audit: 5K Lines Deleted, 48 Tests Added",
    "2026-01-29-ralph-discovery.md": "Claude Code Async Hooks for FastAPI (LL-318)",
    "2026-02-01-journey-to-financial-independence.md": "$5K to $100K: Journey to $6K/Month via Options",
    "2026-02-15-feedback-driven-context-pipelines-2026.md": "Feedback-Driven Context Pipelines (RLHF + RAG)",
    "2026-02-15-paperbanana-automated-architecture-diagrams.md": "PaperBanana: Auto-Generate Architecture Diagrams",
    "2026-02-15-tars-multi-model-routing-trading.md": "TARS: Multi-Model Routing for AI Trading",
    "2026-02-15-tetrate-buildathon-ai-trading-system.md": "Tetrate Buildathon: AI Trading System Entry",
}

def update_title(file_path: Path, new_title: str) -> bool:
    """Update title in frontmatter."""
    content = file_path.read_text()

    # Match title line in frontmatter
    pattern = r'^title:\s*["\']?(.+?)["\']?$'

    def replace_title(match):
        # Preserve quote style if present
        if match.group(0).startswith('title: "'):
            return f'title: "{new_title}"'
        elif match.group(0).startswith("title: '"):
            return f"title: '{new_title}'"
        else:
            return f'title: "{new_title}"'

    updated_content = re.sub(pattern, replace_title, content, count=1, flags=re.MULTILINE)

    if updated_content != content:
        file_path.write_text(updated_content)
        return True
    return False

def main():
    """Process all titles that need shortening."""
    posts_dir = Path("docs/_posts")

    updated = 0

    print("Shortening blog post titles for SEO...\n")

    for filename, new_title in TITLE_UPDATES.items():
        file_path = posts_dir / filename

        if not file_path.exists():
            print(f"⚠️  {filename} not found")
            continue

        if len(new_title) > 60:
            print(f"❌ {filename}: new title still too long ({len(new_title)} chars)")
            continue

        if update_title(file_path, new_title):
            print(f"✅ {filename}")
            print(f"   → {new_title} ({len(new_title)} chars)")
            updated += 1
        else:
            print(f"⏭️  {filename} (no change)")

    print(f"\n{'='*60}")
    print(f"Updated: {updated} titles")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
