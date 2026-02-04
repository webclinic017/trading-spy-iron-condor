#!/usr/bin/env python3
"""
Blog Post Generator - 2026 SEO Best Practices

Based on research:
- Emotional appeal > dry facts
- Story structure: problem → struggle → pivot → lesson
- Personal voice with technical depth
- Specific details, not generic templates
- Engaging headlines that promise value
"""

import subprocess  # nosec B404


def get_recent_commits() -> list[str]:
    """Get last 5 commits for context."""
    try:
        result = subprocess.run(  # nosec B603 B607 - safe git command
            ["git", "log", "--oneline", "-5", "--format=%s"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip().split("\n") if result.returncode == 0 else []
    except Exception:
        return []


def extract_narrative(context: str, signal: str, commits: list[str]) -> dict:
    """
    Extract narrative elements from context and commits.

    Returns dict with:
    - problem: What wasn't working
    - struggle: What was tried and failed
    - pivot: The realization/change
    - solution: What actually worked
    - lesson: Takeaway that applies broadly
    """
    ctx = context.lower()

    # Parse commits for technical details
    recent_work = commits[0] if commits else "recent work"

    narrative = {
        "problem": "",
        "struggle": "",
        "pivot": "",
        "solution": "",
        "lesson": "",
        "technical_context": recent_work,
    }

    # Extract based on keywords in context
    if "browser automation" in ctx and "fail" in ctx:
        narrative["problem"] = "Browser automation kept timing out"
        narrative["struggle"] = "Tried different selectors, waits, persistent contexts"
        narrative["pivot"] = "Realized I was fighting the wrong problem - API exists"
        narrative["solution"] = "Switched to Twitter API v2 with tweepy"
        narrative["lesson"] = (
            "Don't fall in love with your solution, fall in love with solving the problem"
        )

    elif "duplicate" in ctx and ("blog" in ctx or "post" in ctx):
        narrative["problem"] = "Generated 3 duplicate blog posts in 1 hour"
        narrative["struggle"] = "Testing script kept creating new Dev.to posts"
        narrative["pivot"] = "Need duplicate detection before publishing"
        narrative["solution"] = "Check last 10 articles for same title within 2 hours"
        narrative["lesson"] = (
            "Prevent problems at the source, don't just clean up after"
        )

    elif "bot" in ctx and "slop" in ctx:
        narrative["problem"] = "Auto-generated blog posts read like robot wrote them"
        narrative["struggle"] = "Templates and mad-libs create formulaic content"
        narrative["pivot"] = "2026 SEO requires emotional appeal and authentic voice"
        narrative["solution"] = (
            "Extract real narrative from context, write actual stories"
        )
        narrative["lesson"] = "Humans share content that makes them FEEL something"

    # Default: extract from context string directly
    if not narrative["problem"]:
        narrative["problem"] = f"Working on: {context}"
        narrative["solution"] = recent_work
        narrative["lesson"] = "Small wins compound. Keep shipping."

    return narrative


def generate_headline(narrative: dict, signal: str) -> str:
    """
    Generate engaging headline following 2026 best practices:
    - Specific and actionable
    - Promise clear value
    - 50-70 characters for SEO
    - Use power words: "How", "Why", "When", "Failed", "Fixed"
    """

    lesson = narrative["lesson"]

    if "fall in love" in lesson.lower():
        return "When Browser Automation Fails, Pivot Fast"
    elif "prevent problems" in lesson.lower():
        return "How I Fixed Duplicate Blog Posts (The Lazy Way)"
    elif "feel something" in lesson.lower():
        return "Why Your Blog Posts Read Like Bot Slop (And How to Fix It)"
    elif "compound" in lesson.lower():
        return f"Small Wins: {narrative['technical_context'][:40]}"
    else:
        # Default: actionable format
        return f"How I Fixed: {narrative['problem'][:50]}"


def generate_post_content(narrative: dict, signal: str) -> str:
    """Generate blog post with story structure."""

    # Opening hook - emotional, specific
    if signal == "positive":
        hook = f"I {narrative.get('pivot', 'figured something out').replace('Realized ', 'realized ').replace('Need ', 'needed ')}."
    else:
        hook = f"I screwed up: {narrative['problem']}"

    # Story body
    content = f"""{hook}

## The Problem

{narrative['problem']}

"""

    if narrative["struggle"]:
        content += f"""## What I Tried (And Failed)

{narrative['struggle']}

The trap: I kept thinking "just one more thing..." Classic sunk cost fallacy.

"""

    if narrative["pivot"]:
        content += f"""## The Realization

{narrative['pivot']}

This changed everything.

"""

    if narrative["solution"]:
        content += f"""## What Actually Worked

{narrative['solution']}

"""

    # Technical depth - actual code/commands
    if narrative["technical_context"]:
        content += f"""## The Technical Details

Latest commit: `{narrative['technical_context']}`

"""

    # Lesson and tie to larger goal
    content += f"""## The Lesson

{narrative['lesson']}

## Why This Matters

I'm racing toward $600K by my 50th birthday (November 14, 2029) to reach financial independence. Currently at $101K.

Every day counts. Every lesson learned speeds up the path.

This system learns from every mistake and success. After 80+ feedback signals, it's getting smarter.

**The goal: $6K/month passive income. The strategy: compound wins, learn fast, never repeat mistakes.**

---

[Source Code](https://github.com/IgorGanapolsky/trading) | [Progress Dashboard](https://igorganapolsky.github.io/trading/)
"""

    return content


def generate_blog_post(signal: str, context: str) -> dict:
    """Main entry point - generate complete blog post."""

    commits = get_recent_commits()
    narrative = extract_narrative(context, signal, commits)
    headline = generate_headline(narrative, signal)
    content = generate_post_content(narrative, signal)

    return {
        "title": headline,
        "content": content,
        "signal": signal,
        "context": context,
        "tags": [signal, "rlhf", "aitrading", "buildinginpublic"],
    }


if __name__ == "__main__":
    # Test
    test_post = generate_blog_post(
        signal="negative",
        context="bot slop - generated blog posts read like robot wrote them",
    )
    print(test_post["title"])
    print(test_post["content"])
