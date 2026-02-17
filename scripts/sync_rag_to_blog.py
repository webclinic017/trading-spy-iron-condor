#!/usr/bin/env python3
"""
Sync RAG lessons to GitHub Pages blog posts AND Dev.to.

Creates blog posts from RAG lessons for public visibility.
CEO Directive: "We should have blog posts for every day of our journey"
CEO Directive: "You are supposed to be always learning 24/7, and publishing blog posts every day!"
CEO Directive: "Why are lessons so mechanical and boring?? No human will read these blogs!!!!"
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow `python scripts/...` execution where sys.path[0] == scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.content.blog_seo import (
    canonical_url_for_post,
    render_frontmatter,
    truncate_meta_description,
)

try:
    import requests
except ImportError:
    requests = None  # Optional for local runs without requests

# Paths
RAG_LESSONS_DIR = Path(__file__).parent.parent / "rag_knowledge" / "lessons_learned"
BLOG_POSTS_DIR = Path(__file__).parent.parent / "docs" / "_posts"
SNAPSHOT_MANIFEST_PATH = Path(__file__).parent.parent / "docs" / "data" / "alpaca_snapshots.json"

DIAGRAM_BASE_URL = "https://igorganapolsky.github.io/trading/assets"


def _load_snapshot_manifest() -> dict:
    if not SNAPSHOT_MANIFEST_PATH.exists():
        return {}
    try:
        data = SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8")
        parsed = json.loads(data)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _alpaca_snapshot_section_for_post() -> str:
    manifest = _load_snapshot_manifest()
    latest = manifest.get("latest", {}) if isinstance(manifest, dict) else {}
    if not isinstance(latest, dict):
        latest = {}
    paper = latest.get("alpaca_paper", {}) if isinstance(latest.get("alpaca_paper"), dict) else {}
    live = latest.get("alpaca_live", {}) if isinstance(latest.get("alpaca_live"), dict) else {}
    if not paper and not live:
        return ""

    paper_url = paper.get("url", "/trading/assets/snapshots/alpaca_paper_latest.png")
    paper_diagram = paper.get(
        "diagram_url", "/trading/assets/snapshots/paperbanana_paper_latest.svg"
    )
    live_url = live.get("url", "/trading/assets/snapshots/alpaca_live_latest.png")
    live_diagram = live.get("diagram_url", "/trading/assets/snapshots/paperbanana_live_latest.svg")
    paper_time = paper.get("captured_at_utc", "pending")
    live_time = live.get("captured_at_utc", "pending")
    paper_explainer = paper.get(
        "technical_explainer",
        "Paper account technical explanation pending next autonomous capture.",
    )
    live_explainer = live.get(
        "technical_explainer",
        "Brokerage account technical explanation pending next autonomous capture.",
    )

    return f"""
## Alpaca Snapshot + PaperBanana Technical Narrative

### Paper Account
| Alpaca Snapshot | PaperBanana Financial Diagram |
| --- | --- |
| ![Paper Account Snapshot]({paper_url}) | ![Paper Account PaperBanana Diagram]({paper_diagram}) |

Captured: `{paper_time}`

Technical interpretation: {paper_explainer}

### Brokerage Account
| Alpaca Snapshot | PaperBanana Financial Diagram |
| --- | --- |
| ![Brokerage Account Snapshot]({live_url}) | ![Brokerage Account PaperBanana Diagram]({live_diagram}) |

Captured: `{live_time}`

Technical interpretation: {live_explainer}

---
"""


def parse_lesson_file(filepath: Path) -> dict | None:
    """Parse a RAG lesson markdown file."""
    try:
        content = filepath.read_text()

        # Extract metadata
        lesson_id = filepath.stem

        # Try to extract date from filename (e.g., ll_131_..._jan12.md)
        # Use negative lookahead to only match 1-2 digit days, not years like jan2026
        date_match = re.search(r"jan(\d{1,2})(?!\d)", lesson_id, re.IGNORECASE)
        if date_match:
            day = int(date_match.group(1))
            year = 2026
            date_str = f"{year}-01-{day:02d}"
        else:
            # Fallback to today
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Extract title from content
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else lesson_id

        # Extract severity
        severity = "LOW"
        if "severity**: critical" in content.lower() or "severity: critical" in content.lower():
            severity = "CRITICAL"
        elif "severity**: high" in content.lower() or "severity: high" in content.lower():
            severity = "HIGH"
        elif "severity**: medium" in content.lower() or "severity: medium" in content.lower():
            severity = "MEDIUM"

        # Extract category
        category_match = re.search(r"category[:\s*]+([^\n]+)", content, re.IGNORECASE)
        category = category_match.group(1).strip() if category_match else "general"

        return {
            "id": lesson_id,
            "date": date_str,
            "title": title.replace("#", "").strip(),
            "severity": severity,
            "category": category,
            "content": content,
            "filepath": filepath,
        }
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def _truncate_at_sentence(text: str, max_chars: int = 250) -> str:
    """Truncate text at the nearest sentence boundary before max_chars."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]

    # Find last sentence-ending punctuation followed by a space or end of string
    sentence_end = -1
    for match in re.finditer(r"[.!?](?:\s|$)", truncated):
        sentence_end = match.end()

    if sentence_end > 50:
        return truncated[:sentence_end].strip()

    # Fallback: word boundary
    word_end = truncated.rfind(" ")
    if word_end > 50:
        return truncated[:word_end].strip() + "..."

    return truncated.strip() + "..."


def get_engaging_intro(day_num: int, day_of_week: str, lessons: list[dict]) -> str:
    """Generate a unique intro using lesson-specific details."""
    critical = sum(1 for lesson in lessons if lesson["severity"] == "CRITICAL")
    high = sum(1 for lesson in lessons if lesson["severity"] == "HIGH")

    # Find the top lesson title for specificity
    top_lesson = None
    for lesson in lessons:
        if lesson["severity"] == "CRITICAL":
            top_lesson = get_human_readable_title(lesson)
            break
    if not top_lesson:
        for lesson in lessons:
            if lesson["severity"] == "HIGH":
                top_lesson = get_human_readable_title(lesson)
                break

    # Deterministic selection via hash (idempotent per day)
    seed = int(
        hashlib.md5(f"{day_num}-{len(lessons)}-{critical}".encode()).hexdigest()[:8],
        16,
    )

    critical_intros = [
        f"{critical} critical issues hit today. The worst: {top_lesson}. Here's the full breakdown.",
        f"Not a quiet day. {critical} critical failures exposed gaps — {top_lesson} being the most urgent.",
        f"The system flagged {critical} critical problems. {top_lesson} demanded an immediate fix.",
        f"Today tested our resilience. {critical} critical issues, {len(lessons)} total lessons. {top_lesson} was the headline.",
        f"We caught {critical} critical bugs before they could cost real money. Leading the list: {top_lesson}.",
    ]

    weekend_intros = [
        f"Weekend systems check. {len(lessons)} items reviewed while markets rest.",
        f"No trading today, but {len(lessons)} lessons from the week needed documenting.",
        f"Markets closed. We used the time to process {len(lessons)} lessons from recent sessions.",
        f"Weekend review: {len(lessons)} lessons sorted, {critical + high} flagged as high-priority.",
    ]

    friday_intros = [
        f"Week in review. {len(lessons)} lessons captured, {critical} critical.",
        f"Friday wrap. Before Monday's open, here are the {len(lessons)} things we learned.",
        f"End of week. {len(lessons)} lessons, {high} high-priority discoveries.",
        f"Closing the week with {len(lessons)} documented lessons. {critical + high} need attention.",
    ]

    default_intros = [
        f"{len(lessons)} lessons from today's session. {critical} critical, {high} high priority.",
        f"Productive session. {len(lessons)} insights captured from the trading system.",
        f"The system logged {len(lessons)} lessons today. Here's what stood out.",
        f"Steady progress. {len(lessons)} new entries in the knowledge base, {critical + high} worth highlighting.",
        f"Today's haul: {len(lessons)} lessons. The interesting ones are below.",
    ]

    if critical >= 1 and top_lesson:
        pool = critical_intros
    elif day_of_week in ("Saturday", "Sunday"):
        pool = weekend_intros
    elif day_of_week == "Friday":
        pool = friday_intros
    else:
        pool = default_intros

    return pool[seed % len(pool)]


def extract_key_insight(lesson: dict) -> str:
    """Extract the key insight from a lesson, ending at a sentence boundary."""
    content = lesson["content"]

    # Try to find "What Happened" or similar sections
    what_happened = re.search(
        r"(?:What Happened|Problem|Issue|Bug)[:\s]*\n+([^\n#]+)", content, re.IGNORECASE
    )
    if what_happened:
        return _truncate_at_sentence(what_happened.group(1).strip())

    # Try to find the first meaningful paragraph after the title
    paragraphs = re.split(r"\n\n+", content)
    for p in paragraphs[1:4]:  # Skip title, check next 3 paragraphs
        clean = p.strip()
        if len(clean) > 50 and not clean.startswith("#") and not clean.startswith("**"):
            return _truncate_at_sentence(clean)

    # Fallback to first 250 chars without markdown
    clean = re.sub(r"[#*`\[\]]", "", content)
    return _truncate_at_sentence(clean.strip())


def get_lesson_takeaway(lesson: dict) -> str:
    """Extract the actionable takeaway from a lesson."""
    content = lesson["content"]

    # Look for fix/solution/action sections
    fix_match = re.search(
        r"(?:Fix|Solution|Action|Resolution|Takeaway|Prevention)[:\s]*\n+([^\n#]+)",
        content,
        re.IGNORECASE,
    )
    if fix_match:
        result = fix_match.group(1).strip()
        if result:
            return _truncate_at_sentence(result, max_chars=150)

    # Look for bullet points that might be actions
    bullets = re.findall(r"[-*]\s+([A-Z][^.\n]+\.)", content)
    if bullets:
        return _truncate_at_sentence(bullets[0], max_chars=150)

    return ""


def get_human_readable_title(lesson: dict) -> str:
    """Get a human-readable title from the lesson."""
    raw_title = lesson["title"]

    # If title has a colon, take the part after it (usually more descriptive)
    if ":" in raw_title:
        parts = raw_title.split(":", 1)
        if len(parts[1].strip()) > 10:
            title = parts[1].strip()
        else:
            title = raw_title
    else:
        title = raw_title

    # Remove LL- prefix and number patterns
    title = re.sub(r"^LL-?\d+[:\s]*", "", title)
    title = re.sub(r"^\d+[:\s]*", "", title)

    # Clean up underscores and technical formatting
    title = title.replace("_", " ")

    # Remove date suffixes like "jan16" or "(Jan 16, 2026)"
    title = re.sub(r"\s*[-_]?\s*jan\d+\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\([^)]*\d{4}\)\s*$", "", title)

    # Capitalize properly if all lowercase
    if title == title.lower():
        title = title.title()

    # Truncate if too long
    if len(title) > 60:
        title = title[:57] + "..."

    return title.strip() or "Untitled Lesson"


def select_diagram_for_lessons(lessons: list[dict]) -> tuple[str, str]:
    """Select a relevant PaperBanana diagram based on lesson categories/content."""
    all_content = " ".join(lesson.get("content", "").lower() for lesson in lessons)

    if "iron condor" in all_content or "strike" in all_content or "delta" in all_content:
        return (
            f"{DIAGRAM_BASE_URL}/iron_condor_payoff.png",
            "Iron Condor Payoff: defined risk on both sides (PaperBanana)",
        )
    if "theta" in all_content or "expir" in all_content:
        return (
            f"{DIAGRAM_BASE_URL}/theta_decay_curve.png",
            "Theta Decay: why timing matters for exits (PaperBanana)",
        )
    if "rag" in all_content or "knowledge" in all_content or "retriev" in all_content:
        return (
            f"{DIAGRAM_BASE_URL}/rag_retrieval_flow.png",
            "How RAG prevents repeated mistakes (PaperBanana)",
        )
    # Default: Thompson sampling (always relevant for learning posts)
    return (
        f"{DIAGRAM_BASE_URL}/thompson_sampling.png",
        "Thompson Sampling: how the system learns from feedback (PaperBanana)",
    )


def generate_daily_summary_post(date_str: str, lessons: list[dict]) -> str:
    """Generate a human-readable daily blog post from lessons."""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%B %d, %Y")
    day_of_week = date_obj.strftime("%A")

    # Calculate day number (from Oct 29, 2025)
    start_date = datetime(2025, 10, 29)
    day_num = (date_obj - start_date).days + 1

    # Dynamic phase label
    if day_num <= 90:
        phase_label = f"Day {day_num} of 90"
        phase_note = f"**{90 - day_num} days remaining** in the 90-day validation phase."
    else:
        phase_label = f"Day {day_num}"
        phase_note = (
            f"**{phase_label}** — past the initial validation phase, now in continuous operation."
        )

    # Count by severity
    critical = sum(1 for item in lessons if item["severity"] == "CRITICAL")
    high = sum(1 for item in lessons if item["severity"] == "HIGH")

    # Get engaging intro
    intro = get_engaging_intro(day_num, day_of_week, lessons)
    description = truncate_meta_description(intro, max_chars=160)

    # Build the story of today's lessons
    lessons_md = ""

    # Critical lessons first
    critical_lessons = [lesson for lesson in lessons if lesson["severity"] == "CRITICAL"]
    if critical_lessons:
        lessons_md += "\n## The Hard Lessons\n\n"
        for lesson in critical_lessons:
            title = get_human_readable_title(lesson)
            insight = extract_key_insight(lesson)
            takeaway = get_lesson_takeaway(lesson)

            lessons_md += f"### {title}\n\n"
            lessons_md += f"{insight}\n\n"
            if takeaway:
                lessons_md += f"**Key takeaway:** {takeaway}\n\n"

    # High priority lessons
    high_lessons = [lesson for lesson in lessons if lesson["severity"] == "HIGH"]
    if high_lessons:
        lessons_md += "\n## Important Discoveries\n\n"
        for lesson in high_lessons[:3]:
            title = get_human_readable_title(lesson)
            insight = extract_key_insight(lesson)

            lessons_md += f"### {title}\n\n"
            lessons_md += f"{insight}\n\n"

    # Quick wins and improvements
    other_lessons = [lesson for lesson in lessons if lesson["severity"] in ["MEDIUM", "LOW"]]
    if other_lessons:
        lessons_md += "\n## Quick Wins & Refinements\n\n"
        for lesson in other_lessons[:4]:
            title = get_human_readable_title(lesson)
            lessons_md += f"- **{title}** — {_truncate_at_sentence(extract_key_insight(lesson), max_chars=120)}\n"
        lessons_md += "\n"

    # Select a relevant diagram
    img_url, caption = select_diagram_for_lessons(lessons)

    questions = [
        {
            "question": f"What did we learn on {phase_label}?",
            "answer": f"{len(lessons)} lessons captured ({critical} critical, {high} high). {description}",
        },
        {
            "question": "How does this system remember lessons learned?",
            "answer": "We store each lesson in a RAG index and retrieve similar past incidents before future trades and engineering changes.",
        },
        {
            "question": "Where can I browse the full code and history?",
            "answer": "The full repository and daily updates are published publicly on GitHub and GitHub Pages.",
        },
    ]

    frontmatter = render_frontmatter(
        {
            "layout": "post",
            "title": f"{phase_label}: What We Learned — {formatted_date}",
            "description": description,
            "date": date_str,
            "last_modified_at": date_str,
            "image": "/assets/og-image.png",
            "tags": ["lessons-learned", "ai-trading", "rag", "building-in-public"],
            "day_number": day_num,
            "lessons_count": len(lessons),
            "critical_count": critical,
            "excerpt": truncate_meta_description(intro, max_chars=150),
        },
        questions=questions,
    )

    post = (
        frontmatter
        + f"""# {phase_label} | {day_of_week}, {formatted_date}

{phase_note}

{intro}

---
{lessons_md}
---
{_alpaca_snapshot_section_for_post()}

## Today's Numbers

| What | Count |
|------|-------|
| Lessons Learned | **{len(lessons)}** |
| Critical Issues | {critical} |
| High Priority | {high} |
| Improvements | {len(other_lessons)} |

![{caption}]({img_url})
*{caption}*

---

*{phase_label} complete.* [Source on GitHub](https://github.com/IgorGanapolsky/trading) | [Live Dashboard](https://igorganapolsky.github.io/trading/)
"""
    )
    return post


def post_lessons_to_devto(date_str: str, lessons: list[dict]) -> str | None:
    """Post lessons summary to Dev.to."""
    if not requests:
        print("  requests library not available, skipping Dev.to")
        return None

    api_key = os.getenv("DEVTO_API_KEY")
    if not api_key:
        print("  DEVTO_API_KEY not set, skipping Dev.to")
        return None

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%B %d, %Y")
    day_of_week = date_obj.strftime("%A")

    # Calculate day number
    start_date = datetime(2025, 10, 29)
    day_num = (date_obj - start_date).days + 1

    # Dynamic phase label for Dev.to too
    if day_num <= 90:
        phase_label = f"Day {day_num}/90"
    else:
        phase_label = f"Day {day_num}"

    # Count severities
    critical = sum(1 for item in lessons if item["severity"] == "CRITICAL")
    high = sum(1 for item in lessons if item["severity"] == "HIGH")

    intro = get_engaging_intro(day_num, day_of_week, lessons)
    body = f"""## {phase_label} — {day_of_week}, {formatted_date}

{intro}

**{len(lessons)} lessons learned today** ({critical} critical, {high} high priority)

"""
    for lesson in sorted(lessons, key=lambda x: x["severity"], reverse=False)[:5]:
        title = get_human_readable_title(lesson)
        body += f"### {title}\n\n"
        summary = extract_key_insight(lesson)
        body += f"{summary}\n\n"

    body += """---

*Follow our journey: [AI Trading System on GitHub](https://github.com/IgorGanapolsky/trading) | [Blog](https://igorganapolsky.github.io/trading/)*
"""

    headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "article": {
            "title": f"AI Trading: {phase_label} — {len(lessons)} Lessons ({formatted_date})",
            "body_markdown": body,
            "published": True,
            "series": "AI Trading Journey",
            "tags": ["ai", "trading", "machinelearning", "automation"],
            "canonical_url": canonical_url_for_post(date_str, "lessons-learned"),
        }
    }

    try:
        resp = requests.post(
            "https://dev.to/api/articles",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 201:
            url = resp.json().get("url", "")
            print(f"  Published to Dev.to: {url}")
            return url
        else:
            print(f"  Dev.to publish failed: {resp.status_code} - {resp.text[:100]}")
            return None
    except Exception as e:
        print(f"  Dev.to publish error: {e}")
        return None


def sync_lessons_to_blog(publish_devto: bool = True):
    """Main sync function."""
    print("=" * 70)
    print("SYNCING RAG LESSONS TO BLOG" + (" + DEV.TO" if publish_devto else ""))
    print("=" * 70)

    # Ensure directories exist
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)

    if not RAG_LESSONS_DIR.exists():
        print(f"ERROR: RAG lessons directory not found: {RAG_LESSONS_DIR}")
        return

    # Parse all lessons
    lessons_by_date: dict[str, list[dict]] = {}

    for lesson_file in RAG_LESSONS_DIR.glob("*.md"):
        lesson = parse_lesson_file(lesson_file)
        if lesson:
            date_str = lesson["date"]
            if date_str not in lessons_by_date:
                lessons_by_date[date_str] = []
            lessons_by_date[date_str].append(lesson)

    print(
        f"Found {sum(len(v) for v in lessons_by_date.values())} lessons across {len(lessons_by_date)} days"
    )

    # Generate blog posts for each day
    created = 0
    skipped = 0
    devto_published = 0
    created_files: list[Path] = []

    for date_str, lessons in sorted(lessons_by_date.items()):
        # Generate filename
        filename = f"{date_str}-lessons-learned.md"
        filepath = BLOG_POSTS_DIR / filename

        # Generate post content
        post_content = generate_daily_summary_post(date_str, lessons)

        # Check if already exists with same content
        if filepath.exists():
            existing = filepath.read_text()
            if f"lessons_count: {len(lessons)}" in existing:
                print(f"  SKIP {filename} (already up to date)")
                skipped += 1
                continue

        # Write post
        filepath.write_text(post_content)
        print(f"  CREATE {filename} ({len(lessons)} lessons)")
        created += 1
        created_files.append(filepath)

        # Publish to Dev.to for new posts
        if publish_devto:
            url = post_lessons_to_devto(date_str, lessons)
            if url:
                devto_published += 1

    print("\n" + "=" * 70)
    print(f"SYNC COMPLETE: {created} created, {skipped} skipped, {devto_published} to Dev.to")
    print("=" * 70)

    # Lint newly created posts (warn-only by default)
    if created_files:
        try:
            import subprocess
            import sys

            lint_args = [sys.executable, "scripts/lint_blog_posts.py", "--paths"]
            lint_args.extend([str(p) for p in created_files])
            if os.getenv("BLOG_LINT_STRICT", "").lower() in {"1", "true", "yes"}:
                lint_args.append("--strict")
            else:
                lint_args.append("--warn-only")

            result = subprocess.run(lint_args, check=False, text=True)
            if result.returncode != 0:
                print("WARNING: Blog linting reported issues.")
        except Exception as exc:
            print(f"WARNING: Blog linting failed: {exc}")

    # Refresh RAG query index for the UI/worker after syncing lessons.
    try:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/build_rag_query_index.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Updated data/rag/lessons_query.json")
        else:
            print("WARNING: Failed to update lessons_query.json")
            print(result.stdout.strip())
            print(result.stderr.strip())
    except Exception as exc:
        print(f"WARNING: Unable to update lessons_query.json: {exc}")

    return created, skipped


if __name__ == "__main__":
    import sys

    publish_devto = "--no-devto" not in sys.argv
    sync_lessons_to_blog(publish_devto=publish_devto)
